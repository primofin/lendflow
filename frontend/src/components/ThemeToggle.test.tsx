import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it } from "vitest";

import { ThemeToggle } from "./ThemeToggle";

afterEach(() => {
  delete document.documentElement.dataset.theme;
  localStorage.clear();
});

describe("ThemeToggle", () => {
  it("offers dark from the light theme, applies it and remembers it", async () => {
    document.documentElement.dataset.theme = "light";
    render(<ThemeToggle />);

    await userEvent.click(screen.getByRole("button", { name: "Switch to dark theme" }));

    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("lendflow-theme")).toBe("dark");
    expect(await screen.findByRole("button", { name: "Switch to light theme" })).toBeInTheDocument();
  });

  it("switches back to light", async () => {
    document.documentElement.dataset.theme = "dark";
    render(<ThemeToggle />);

    await userEvent.click(screen.getByRole("button", { name: "Switch to light theme" }));

    expect(document.documentElement.dataset.theme).toBe("light");
    expect(localStorage.getItem("lendflow-theme")).toBe("light");
  });
});
