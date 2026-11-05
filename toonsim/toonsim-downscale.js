/*
 * ToonSim: never enlarge the simulated Toon screen.
 *
 * noVNC's "Local scaling" fits the remote framebuffer to the browser
 * viewport in both directions. A Toon 1 is 800x480 and a Toon 2 is
 * 1024x600, so enlarging them on a larger monitor makes the simulated
 * resolution wrong. Keep 1:1 when there is room, but still shrink when the
 * browser viewport is smaller.
 */
import Display from "../core/display.js";

const autoscale = Display.prototype.autoscale;

Display.prototype.autoscale = function (containerWidth, containerHeight) {
    autoscale.call(this, containerWidth, containerHeight);

    // autoscale() already picked the largest fitting ratio. Only clamp the
    // upward direction; values below 1 still shrink for small viewports.
    if (this.scale > 1.0) {
        this.scale = 1.0;
    }
};
