/*
 * Keeps a dash-mantine-components MultiSelect (.single-row-ms) clamped to a
 * single row and renders a "+N more" counter for the selections that overflow.
 *
 * Mantine 7's MultiSelect has no native max-displayed-values support, so this
 * works directly on the rendered DOM:
 *   - the pills container is forced to nowrap + hidden overflow (hard cap), and
 *   - pills past the available width are hidden and tallied into .ms-overflow-badge.
 *
 * It is class-name-agnostic (locates pills via [class*="Pill-root"]) and driven
 * by MutationObserver + ResizeObserver so it re-applies after every Mantine
 * re-render. No Dash callback is involved.
 */
(function () {
  "use strict";

  var ROOT_SELECTOR = ".single-row-ms";
  var BADGE_RESERVE = 72; // px reserved on the right for the "+N more" badge

  function findPills(root) {
    return Array.prototype.slice.call(
      root.querySelectorAll('[class*="Pill-root"]')
    );
  }

  function recompute(root) {
    var wrapper = root.closest(".ms-wrapper");
    var badge = wrapper && wrapper.querySelector(".ms-overflow-badge");
    if (!badge) return;

    var pills = findPills(root);
    if (pills.length === 0) {
      badge.style.display = "none";
      return;
    }

    var field = pills[0].parentElement;

    // Hard cap: this container can never grow beyond one row.
    field.style.flexWrap = "nowrap";
    field.style.overflow = "hidden";

    // Reset visibility before measuring.
    pills.forEach(function (p) {
      p.style.display = "";
    });

    var fieldStyle = window.getComputedStyle(field);
    var gap = parseFloat(fieldStyle.columnGap || fieldStyle.gap || "0") || 4;

    // First pass: does everything fit without needing the badge?
    var total = pills.reduce(function (sum, p) {
      return sum + p.offsetWidth + gap;
    }, 0);

    var hidden = 0;

    if (total > field.clientWidth) {
      var available = field.clientWidth - BADGE_RESERVE;
      var used = 0;
      for (var i = 0; i < pills.length; i++) {
        if (hidden > 0) {
          pills[i].style.display = "none";
          hidden++;
          continue;
        }
        used += pills[i].offsetWidth + gap;
        if (used > available) {
          pills[i].style.display = "none";
          hidden = 1;
        }
      }
    }

    if (hidden > 0) {
      badge.textContent = "+" + hidden + " more";
      badge.style.display = "flex";
      // Vertically align the badge with the input control.
      var wrapRect = wrapper.getBoundingClientRect();
      var fieldRect = field.getBoundingClientRect();
      badge.style.top = fieldRect.top - wrapRect.top + fieldRect.height / 2 + "px";
    } else {
      badge.style.display = "none";
    }
  }

  function attach(root) {
    if (root.__singleRowAttached) return;
    root.__singleRowAttached = true;

    var scheduled = false;
    var run = function () {
      if (scheduled) return;
      scheduled = true;
      window.requestAnimationFrame(function () {
        scheduled = false;
        recompute(root);
      });
    };

    // childList only: pills are added/removed as selections change. We avoid
    // observing attributes so our own style writes don't re-trigger the loop.
    new MutationObserver(run).observe(root, { childList: true, subtree: true });

    if (window.ResizeObserver) {
      new ResizeObserver(run).observe(root);
    }
    window.addEventListener("resize", run);

    run();
  }

  function scan() {
    document.querySelectorAll(ROOT_SELECTOR).forEach(attach);
  }

  function init() {
    scan();
    // The MultiSelect can mount after first paint (modal render, hot reload),
    // so keep watching the document for it to appear.
    new MutationObserver(scan).observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
