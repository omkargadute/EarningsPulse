import { expect, test } from "@playwright/test";

test.describe("Home page", () => {
  test("loads hero and ticker input", async ({ page }) => {
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: /Know the report/i })
    ).toBeVisible();
    await expect(
      page.getByRole("combobox", { name: /stock ticker/i })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: /generate playbook/i })
    ).toBeVisible();
  });

  test("shows disclaimer banner", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByText(/not financial advice/i)).toBeVisible();
  });
});

test.describe("Demo playbook flow", () => {
  test("loads instant demo and renders playbook sections", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /demo aapl/i }).click();

    await expect(page).toHaveURL(/\/playbook\/demo_aapl/);
    await expect(
      page.getByRole("heading", { name: /Apple Inc\. Earnings Playbook/i })
    ).toBeVisible({ timeout: 15_000 });

    await expect(page.getByRole("heading", { name: "Report Forecast" })).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Price Reaction Scenarios" })
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Peer Spillover Map" })
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Action Playbook" })).toBeVisible();
    await expect(
      page.getByRole("region", { name: /reaction workspace/i }).getByText("AAPL")
    ).toBeVisible();
  });

  test("export toolbar is visible on completed demo", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("button", { name: /demo aapl/i }).click();
    await expect(page).toHaveURL(/\/playbook\/demo_aapl/);

    await expect(page.getByText("Export playbook")).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByRole("button", { name: /^JSON$/i })).toBeVisible();
    await expect(
      page.getByRole("button", { name: /print \/ pdf/i })
    ).toBeVisible();
  });
});

test.describe("Calendar page", () => {
  test("loads calendar view", async ({ page }) => {
    await page.goto("/calendar");
    await expect(
      page.getByRole("heading", { name: /earnings calendar/i })
    ).toBeVisible();
  });
});

test.describe("Generation stream contract", () => {
  for (const failed of [false, true]) {
    test(failed ? "shows terminal generation failure" : "continues after a tool failure and exports JSON", async ({ page, request }) => {
      const backend = process.env.BACKEND_URL ?? "http://localhost:8000";
      await request.post(`${backend}/api/playbook/demo/AAPL`);
      const demo = await (await request.get(`${backend}/api/playbook/demo_aapl`)).json();
      let completed = false;
      let statusLoaded: () => void = () => {};
      const initialStatus = new Promise<void>((resolve) => { statusLoaded = resolve; });
      await page.route("**/api/playbook/generate", (route) => route.fulfill({
        json: { job_id: "job_browser", ticker: "AAPL", status: "pending", stream_url: "/api/playbook/stream/job_browser" },
      }));
      await page.route("**/api/playbook/job_browser", async (route) => {
        await route.fulfill({
        json: { ...demo, job_id: "job_browser", status: completed ? (failed ? "failed" : "completed") : "running", playbook: completed && !failed ? demo.playbook : null, error: failed && completed ? "Provider unavailable" : null },
        });
        statusLoaded();
      });
      await page.route("**/api/playbook/stream/job_browser", async (route) => {
        await initialStatus;
        completed = true;
        const payloads = [
          { type: "tool_call", job_id: "job_browser", message: "News unavailable; using fallback", trace: { event_id: "tool_failed", job_id: "job_browser", event_type: "tool_call_failed", timestamp: new Date().toISOString(), message: "News unavailable; using fallback" } },
          failed ? { type: "error", error: "Provider unavailable" } : { type: "playbook_ready", job_id: "job_browser", ticker: "AAPL" },
        ];
        await route.fulfill({ contentType: "text/event-stream", body: payloads.map((event) => `data: ${JSON.stringify(event)}\n\n`).join("") });
      });
      await page.goto("/");
      await page.getByRole("combobox", { name: /stock ticker/i }).fill("AAPL");
      await page.getByRole("button", { name: /generate playbook/i }).click();
      await expect(page).toHaveURL(/\/playbook\/job_browser/);
      if (failed) {
        await expect(page.getByRole("heading", { name: "The playbook could not be finished" })).toBeVisible();
        await expect(page.getByText("Provider unavailable", { exact: true })).toBeVisible();
      } else {
        await expect(page.getByRole("heading", { name: /Apple Inc\. Earnings Playbook/i })).toBeVisible();
        const download = page.waitForEvent("download");
        await page.getByRole("button", { name: /^JSON$/ }).click();
        expect((await download).suggestedFilename()).toMatch(/\.json$/);
      }
    });
  }
});
