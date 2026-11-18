import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { setAccessToken } from "@/lib/api/client";

import { MyApplications } from "./MyApplications";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  setAccessToken("tok");
});

describe("LF-012 MyApplications", () => {
  it("links each application to its tracker, in the order given", async () => {
    fetchMock.mockResolvedValue(
      Response.json([
        { id: "new", status: "SUBMITTED", amount_vnd: 50_000_000, term_months: 12, submitted_at: null },
        { id: "old", status: "APPROVED", amount_vnd: 90_000_000, term_months: 24, submitted_at: null },
      ]),
    );
    render(<MyApplications />);

    const links = await screen.findAllByRole("link");
    expect(links.map((l) => l.getAttribute("href"))).toEqual(["/applications/new", "/applications/old"]);
    expect(links[0]).toHaveTextContent("50,000,000 VND over 12 months");
  });

  it("invites a first application when there are none", async () => {
    fetchMock.mockResolvedValue(Response.json([]));
    render(<MyApplications />);

    expect(await screen.findByText(/You have no applications yet/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Apply for a loan" })).toHaveAttribute("href", "/apply");
  });

  it("says so when the list cannot be loaded", async () => {
    fetchMock.mockResolvedValue(Response.json({ detail: "x" }, { status: 500 }));
    render(<MyApplications />);

    expect(await screen.findByRole("alert")).toHaveTextContent(/could not be loaded/);
  });
});
