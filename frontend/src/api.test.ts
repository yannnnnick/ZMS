import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "./api";

interface MockResponse {
  ok: boolean;
  status: number;
  json?: () => Promise<unknown>;
}

function mockFetch(response: MockResponse) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: response.ok,
    status: response.status,
    json: response.json ?? (() => Promise.resolve({}))
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("returns parsed JSON and sends credentialed requests", async () => {
    const fetchMock = mockFetch({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ role: "admin", display_name: "Ada", csrf_token: "t" })
    });

    const session = await api.login("admin@example.test", "Admin12345!");

    expect(session.role).toBe("admin");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/login");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
  });

  it("throws an ApiError carrying the backend detail on failure", async () => {
    mockFetch({ ok: false, status: 403, json: () => Promise.resolve({ detail: "Invalid CSRF token" }) });

    await expect(api.animals()).rejects.toMatchObject({ status: 403, message: "Invalid CSRF token" });
  });

  it("flattens validation error arrays into a single message", async () => {
    mockFetch({
      ok: false,
      status: 422,
      json: () => Promise.resolve({ detail: [{ msg: "field required" }, { msg: "too short" }] })
    });

    await expect(api.animals()).rejects.toMatchObject({
      status: 422,
      message: "field required; too short"
    });
  });

  it("attaches the CSRF and content-type headers on mutations", async () => {
    const fetchMock = mockFetch({ ok: true, status: 201, json: () => Promise.resolve({ id: 1 }) });

    await api.createSpecies("csrf-123", { common_name: "X", category: "Y" });

    const headers = fetchMock.mock.calls[0][1].headers as Headers;
    expect(headers.get("X-CSRF-Token")).toBe("csrf-123");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("resolves to undefined for 204 No Content responses", async () => {
    mockFetch({ ok: true, status: 204 });

    await expect(api.deleteAnimal("csrf", 1)).resolves.toBeUndefined();
  });
});
