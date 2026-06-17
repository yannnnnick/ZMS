import { describe, expect, it } from "vitest";
import { optionalText } from "./formHelpers";

describe("optionalText", () => {
  it("returns the original string if there are no extra spaces", () => {
    expect(optionalText("hello")).toBe("hello");
  });

  it("returns the trimmed string if there are leading or trailing spaces", () => {
    expect(optionalText("  hello world  ")).toBe("hello world");
  });

  it("returns null for an empty string", () => {
    expect(optionalText("")).toBeNull();
  });

  it("returns null for a string containing only whitespaces", () => {
    expect(optionalText("   ")).toBeNull();
    expect(optionalText("\t\n")).toBeNull();
  });
});
