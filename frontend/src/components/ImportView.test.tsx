import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";
import type { ImportResult } from "@/lib/api/types";

import { ImportView } from "./ImportView";

const fetchMock = vi.fn<typeof fetch>();

const result: ImportResult = {
  job_id: "j1",
  total_rows: 3,
  imported: 1,
  duplicates: 1,
  invalid: 1,
  issues: [
    { row: 3, kind: "invalid", message: "national_id: National ID must be 12 digits" },
    { row: 4, kind: "duplicate", message: "Duplicate of row 2 in this file; skipped" },
  ],
  created: [{ row: 2, application_id: "a1" }],
};

function csv(name = "people.csv", size = 10) {
  const file = new File(["x".repeat(size)], name, { type: "text/csv" });
  return file;
}

function posts() {
  return fetchMock.mock.calls.filter(([, init]) => init?.method === "POST");
}

beforeEach(() => {
  fetchMock.mockReset();
  fetchMock.mockImplementation(async (input, init) => {
    if (init?.method === "POST") return Response.json(result, { status: 201 });
    return new Response(new Blob(["email\n"], { type: "text/csv" }));
  });
  vi.stubGlobal("fetch", fetchMock);
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: vi.fn(() => "blob:x"), revokeObjectURL: vi.fn() }));
  setAccessToken("tok");
});

describe("LF-013 ImportView", () => {
  it("uploads the file and shows the counts, the row issues and links to the drafts", async () => {
    render(<ImportView />);
    await userEvent.upload(screen.getByLabelText("CSV file"), csv());
    await userEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(await screen.findByTestId("import-result")).toBeInTheDocument();
    expect(String(posts()[0][0])).toBe("/api/imports/applications");
    expect(screen.getByTestId("count-total")).toHaveTextContent("3");
    expect(screen.getByTestId("count-imported")).toHaveTextContent("1");
    expect(screen.getByTestId("count-duplicates")).toHaveTextContent("1");
    expect(screen.getByTestId("count-invalid")).toHaveTextContent("1");
    expect(screen.getByTestId("issues")).toHaveTextContent("National ID must be 12 digits");
    expect(screen.getByTestId("issues")).toHaveTextContent("Skipped");
    expect(screen.getByRole("link", { name: "open the draft" })).toHaveAttribute("href", "/review/a1");
    expect(screen.getByRole("button", { name: "Download the error report" })).toBeInTheDocument();
  });

  it("offers no error report when every row was fine", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ ...result, issues: [], duplicates: 0, invalid: 0 }, { status: 201 }),
    );
    render(<ImportView />);
    await userEvent.upload(screen.getByLabelText("CSV file"), csv());
    await userEvent.click(screen.getByRole("button", { name: "Import" }));

    await screen.findByTestId("import-result");
    expect(screen.queryByRole("button", { name: "Download the error report" })).not.toBeInTheDocument();
  });

  it("refuses a missing file, a non-CSV file and an oversized file without sending anything", async () => {
    render(<ImportView />);
    await userEvent.click(screen.getByRole("button", { name: "Import" }));
    expect(await screen.findByText("Choose a CSV file first.")).toBeInTheDocument();

    await userEvent.upload(screen.getByLabelText("CSV file"), csv("people.txt"), { applyAccept: false });
    await userEvent.click(screen.getByRole("button", { name: "Import" }));
    expect(await screen.findByText("Choose a .csv file.")).toBeInTheDocument();

    await userEvent.upload(screen.getByLabelText("CSV file"), csv("big.csv", 2 * 1024 * 1024 + 1));
    await userEvent.click(screen.getByRole("button", { name: "Import" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/2 MB or smaller/);
    expect(posts()).toHaveLength(0);
  });

  it("shows the server's refusal, such as wrong columns", async () => {
    fetchMock.mockImplementation(async () =>
      Response.json({ detail: "Missing columns: term_months. Use the template's column names." }, { status: 422 }),
    );
    render(<ImportView />);
    await userEvent.upload(screen.getByLabelText("CSV file"), csv());
    await userEvent.click(screen.getByRole("button", { name: "Import" }));

    expect(await screen.findByText(/Missing columns: term_months/)).toBeInTheDocument();
    expect(screen.queryByTestId("import-result")).not.toBeInTheDocument();
  });

  it("downloads the template through an authorised request", async () => {
    render(<ImportView />);
    await userEvent.click(screen.getByRole("button", { name: "Download the template" }));

    await waitFor(() =>
      expect(fetchMock.mock.calls.some(([url]) => String(url) === "/api/imports/applications/template")).toBe(true),
    );
  });
});
