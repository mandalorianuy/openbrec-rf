import { chromium } from "playwright";

const baseURL = process.env.OPENBREC_UI_BASE_URL ?? "http://127.0.0.1:4173";
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  locale: "es-UY",
  timezoneId: "America/Montevideo",
  viewport: { width: 1440, height: 1000 },
});
const page = await context.newPage();
const consoleErrors = [];
page.on("console", (message) => {
  if (message.type() === "error") consoleErrors.push(message.text());
});
page.on("pageerror", (error) => consoleErrors.push(error.message));

try {
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await page.getByTestId("operations-map").waitFor();
  await page.getByTestId("capability-matrix").waitFor();
  await page.getByTestId("event-timeline").waitFor();
  await page.getByTestId("semantic-inspector").waitFor();
  await page.getByText("Abstención", { exact: true }).first().waitFor();
  await page.getByText("Capacidades ausentes", { exact: true }).waitFor();

  await page.getByLabel("Seleccionar Sector Alpha").click();
  await page.getByTestId("semantic-inspector").getByText("zone-alpha", { exact: true }).waitFor();
  await page.getByRole("button", { name: "Inferencia", exact: true }).click();
  const inferenceEvents = await page.getByTestId("event-timeline").locator("li").count();
  if (inferenceEvents !== 3) throw new Error(`expected 3 inference events, got ${inferenceEvents}`);

  await page.evaluate(() => navigator.serviceWorker.ready);
  await page.reload({ waitUntil: "networkidle" });
  await page.getByTestId("operations-map").waitFor();
  await context.setOffline(true);
  await page.reload({ waitUntil: "domcontentloaded" });
  await page.getByTestId("operations-map").waitFor();
  await page.getByText("Replay offline", { exact: true }).waitFor();
  await page.getByTestId("semantic-inspector").getByText("zone-bravo", { exact: true }).waitFor();
  await page.getByText("Abstención", { exact: true }).first().waitFor();

  if (consoleErrors.length) throw new Error(`browser console errors: ${consoleErrors.join(" | ")}`);
  console.log(JSON.stringify({
    browser: "chromium",
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
