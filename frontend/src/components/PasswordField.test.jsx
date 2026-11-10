import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import PasswordField from "./PasswordField.jsx";

describe("PasswordField", () => {
  it("hides the password by default", () => {
    render(<PasswordField id="password" value="secret" onChange={vi.fn()} />);
    expect(screen.getByPlaceholderText("Password")).toHaveAttribute("type", "password");
  });

  it("reveals the password while the toggle button is held down, and hides it again on release", () => {
    render(<PasswordField id="password" value="secret" onChange={vi.fn()} />);
    const input = screen.getByPlaceholderText("Password");
    const toggle = screen.getByRole("button", { name: /hold to show password/i });

    fireEvent.mouseDown(toggle);
    expect(input).toHaveAttribute("type", "text");

    fireEvent.mouseUp(toggle);
    expect(input).toHaveAttribute("type", "password");
  });

  it("calls onChange when the user types", () => {
    const onChange = vi.fn();
    render(<PasswordField id="password" value="" onChange={onChange} />);
    fireEvent.change(screen.getByPlaceholderText("Password"), { target: { value: "abc" } });
    expect(onChange).toHaveBeenCalled();
  });
});
