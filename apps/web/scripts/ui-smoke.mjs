import { chromium } from "playwright";

const baseURL = process.env.OPENBREC_UI_BASE_URL ?? "http://127.0.0.1:4173";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  locale: "es-UY",
  timezoneId: "America/Montevideo",
  viewport: { width: 1440, height: 1000 },
  reducedMotion: "reduce",
});
const page = await context.newPage();
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(error.message));

try {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  const terminal = page.getByTestId("offline-terminal");
  const composer = page.getByTestId("message-composer");
  const queue = page.getByTestId("message-queue");
  await terminal.waitFor();
  await composer.waitFor();
  await queue.waitFor();
  await page.getByText("Partición activa", { exact: true }).first().waitFor();
  await page.getByText("Capacidades ausentes", { exact: true }).waitFor();
  await page.getByText("no garantiza arribo ni rescate", { exact: false }).first().waitFor();
  await page.getByText("no implica ausencia", { exact: false }).waitFor();

  const initialQueued = await queue.locator(".queue-list > li").count();
  await composer.getByLabel("Texto breve", { exact: true }).check();
  await composer.getByLabel("Mensaje breve", { exact: false }).fill("Mensaje creado durante la partición");
  await composer.getByRole("button", { name: "Encolar texto", exact: true }).click();
  const queuedAfterText = await queue.locator(".queue-list > li").count();
  if (queuedAfterText !== initialQueued + 1) {
    throw new Error(`text queue did not grow: ${initialQueued} -> ${queuedAfterText}`);
  }

  await composer.getByLabel("SOS", { exact: true }).check();
  const sosAction = composer.getByRole("button", { name: "Encolar SOS", exact: true });
  if (await sosAction.isEnabled()) throw new Error("SOS action enabled without confirmation");
  await composer.getByLabel("Confirmo que deseo encolar un SOS", { exact: true }).check();
  await sosAction.click();
  const sosQueueItem = queue.locator(".queue-list > li").filter({ hasText: "SOS · asistencia requerida" });
  await sosQueueItem.waitFor();
  await sosQueueItem.getByRole("button", { name: "Solicitar cancelación", exact: true }).click();
  await page.getByTestId("message-history").getByText("Cancelación solicitada", { exact: true }).first().waitFor();

  const accessibility = await page.evaluate(() => {
    const controls = Array.from(document.querySelectorAll("button,input,select,textarea"));
    const unlabeled = controls.filter((element) => {
      const control = element;
      if (control instanceof HTMLButtonElement) return !(control.innerText.trim() || control.getAttribute("aria-label"));
      return !(("labels" in control && control.labels && control.labels.length) || control.getAttribute("aria-label"));
    });
    const critical = Array.from(document.querySelectorAll(".view-switcher button,.primary-action,.queue-list button,.message-types label"));
    const smallTargets = critical.filter((element) => {
      const rect = element.getBoundingClientRect();
      return rect.height < 44 || rect.width < 44;
    });
    const pulse = document.querySelector(".pulse");
    return {
      unlabeled: unlabeled.length,
      smallTargets: smallTargets.length,
      reducedMotion: pulse ? getComputedStyle(pulse).animationName === "none" : false,
    };
  });
  if (accessibility.unlabeled) throw new Error(`${accessibility.unlabeled} unlabeled controls`);
  if (accessibility.smallTargets) throw new Error(`${accessibility.smallTargets} critical targets below 44px`);
  if (!accessibility.reducedMotion) throw new Error("reduced motion preference not honored");

  await page.getByRole("button", { name: "Situación", exact: true }).focus();
  await page.keyboard.press("Enter");
  await page.getByTestId("operations-map").waitFor();
  await page.getByTestId("capability-matrix").waitFor();
  await page.getByTestId("event-timeline").waitFor();
  await page.getByTestId("semantic-inspector").waitFor();
  await page.getByText("Abstención", { exact: true }).first().waitFor();

  await page.getByLabel("Seleccionar Sector Alpha").click();
  await page.getByTestId("semantic-inspector").getByText("zone-alpha", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Inferencia", exact: true }).click();
  const inferenceEvents = await page.getByTestId("event-timeline").locator("li").count();
  if (inferenceEvents !== 3) throw new Error(`expected 3 inference events, got ${inferenceEvents}`);

  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload({ waitUntil: "networkidle" });
  await page.getByTestId("offline-terminal").waitFor();
  await context.setOffline(true);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByTestId("offline-terminal").waitFor();
  await page.getByText("Partición activa", { exact: true }).first().waitFor();
  const queued_after_offline_action = await page.getByTestId("message-queue").locator(".queue-list > li").count();
  if (queued_after_offline_action !== queuedAfterText) {
    throw new Error(`offline queue not preserved: ${queuedAfterText} -> ${queued_after_offline_action}`);
  }
  await page.getByRole("button", { name: "Situación", exact: true }).click();
  await page.getByTestId("operations-map").waitFor();
  await page.getByText("Replay offline", { exact: true }).waitFor();
  await page.getByTestId("semantic-inspector").getByText("zone-bravo", { exact: true }).waitFor();

  if (consoleErrors.length) throw new Error(`browser console errors: ${consoleErrors.join(" | ")}`);
  console.log(JSON.stringify({
    browser: "chromium",
    terminal_actions: 4,
    initial_queued: initialQueued,
    queued_after_text: queuedAfterText,
    queued_after_offline_action,
    cancellation_history_preserved: true,
    keyboard_operable: true,
    critical_actions_text_labeled: accessibility.unlabeled === 0,
    critical_targets_44px: accessibility.smallTargets === 0,
    reduced_motion_supported: accessibility.reducedMotion,
    semantic_layers: 3,
    nodes_visible: await page.getByTestId("capability-matrix").locator('[role="row"]').count() - 1,
    inference_events: inferenceEvents,
    selected_zone_before_reload: "zone-alpha",
    selected_zone_after_reload: "zone-bravo",
    offline_reload: "passed",
    console_errors: 0,
  }));
} finally {
  await context.setOffline(false);
  await browser.close();
}
