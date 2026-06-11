import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginScreen } from "./LoginScreen";
import { api, ApiError } from "../api";

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return { ...actual, api: { ...actual.api, login: vi.fn() } };
});

const loginMock = vi.mocked(api.login);

describe("LoginScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("submits the entered credentials and forwards the session", async () => {
    const session = { role: "admin", display_name: "Ada", csrf_token: "t" } as const;
    loginMock.mockResolvedValue(session);
    const onLogin = vi.fn();

    render(<LoginScreen onLogin={onLogin} onOpenPublicMap={() => {}} />);
    await userEvent.type(screen.getByLabelText("E-Mail"), "admin@example.test");
    await userEvent.type(screen.getByLabelText("Passwort"), "Admin12345!");
    await userEvent.click(screen.getByRole("button", { name: /Einloggen/i }));

    expect(loginMock).toHaveBeenCalledWith("admin@example.test", "Admin12345!");
    expect(onLogin).toHaveBeenCalledWith(session);
  });

  it("shows the backend error message when login fails", async () => {
    loginMock.mockRejectedValue(new ApiError(401, "Invalid email or password"));
    const onLogin = vi.fn();

    render(<LoginScreen onLogin={onLogin} onOpenPublicMap={() => {}} />);
    await userEvent.type(screen.getByLabelText("E-Mail"), "admin@example.test");
    await userEvent.type(screen.getByLabelText("Passwort"), "Wrong12345!");
    await userEvent.click(screen.getByRole("button", { name: /Einloggen/i }));

    expect(await screen.findByText("Invalid email or password")).toBeInTheDocument();
    expect(onLogin).not.toHaveBeenCalled();
  });
});
