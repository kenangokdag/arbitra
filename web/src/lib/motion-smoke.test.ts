// V1-S13 P001: motion library import smoke test.
// Plan: docs/plans/V1_S13_demo_path_polish.md §4.

import { describe, it, expect } from "vitest";
import { motion, useReducedMotion, AnimatePresence } from "motion/react";

describe("motion library smoke", () => {
  it("exports motion namespace with HTML primitives", () => {
    expect(motion.div).toBeDefined();
    expect(motion.section).toBeDefined();
    expect(motion.span).toBeDefined();
  });

  it("exports useReducedMotion hook", () => {
    expect(typeof useReducedMotion).toBe("function");
  });

  it("exports AnimatePresence component", () => {
    expect(AnimatePresence).toBeDefined();
  });
});
