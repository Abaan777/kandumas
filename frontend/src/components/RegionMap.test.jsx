import { describe, expect, it } from "vitest";
import { heatColor } from "./RegionMap.jsx";

describe("heatColor", () => {
  it("returns a neutral gray when there's no accuracy value yet", () => {
    expect(heatColor(null)).toBe("rgb(154, 165, 163)");
  });

  it("is hot red at the top of the scale", () => {
    expect(heatColor(100)).toBe("rgb(199, 46, 46)");
  });

  it("is cool blue at the bottom of the scale", () => {
    expect(heatColor(0)).toBe("rgb(58, 110, 165)");
  });

  it("is warmer (more red, less blue) for a higher percentage", () => {
    const cool = heatColor(20);
    const hot = heatColor(90);
    const redOf = (rgb) => Number(rgb.match(/\d+/g)[0]);
    const blueOf = (rgb) => Number(rgb.match(/\d+/g)[2]);
    expect(redOf(hot)).toBeGreaterThan(redOf(cool));
    expect(blueOf(hot)).toBeLessThan(blueOf(cool));
  });

  it("clamps out-of-range values instead of producing nonsense colors", () => {
    expect(heatColor(150)).toBe(heatColor(100));
    expect(heatColor(-20)).toBe(heatColor(0));
  });
});
