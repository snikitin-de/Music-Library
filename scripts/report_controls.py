"""Progressive enhancement for standalone report controls and chart rendering."""

from html import escape


def page_actions_html(menu_id: str, label: str, buttons: str) -> str:
    return f"""<details class="page-actions" id="{escape(menu_id)}">
        <summary aria-label="{escape(label)}" title="{escape(label)}">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>
          </svg>
        </summary>
        <div class="topbar-settings-panel page-actions-panel report-menu">
          {buttons}
        </div>
      </details>"""


REPORT_PANEL_LAYOUT_JS = r"""
const reportPaneWidths = {
  sidebar: {min: 188, max: 440},
  queue: {min: 280, max: 520},
};

function reportPaneMaximum(pane, space, neighbour) {
  const {min, max} = reportPaneWidths[pane];
  return Math.max(min, Math.min(max, space - neighbour));
}

function fitReportPanels(width, gap, sidebar, queue, collapsed, docked) {
  const space = width - gap * (docked ? 4 : 3) - 400;
  const sidebarMinimum = reportPaneWidths.sidebar.min;
  const queueMinimum = reportPaneWidths.queue.min;
  const left = collapsed ? 72 : Math.max(sidebarMinimum,
    Math.min(sidebar, reportPaneMaximum('sidebar', space, docked ? queueMinimum : 0)));
  const right = docked ? Math.max(queueMinimum, Math.min(queue, reportPaneMaximum('queue', space, left))) : 0;
  return {sidebar: left, queue: right, space};
}

function setupReportPanelWidths(shell) {
  const queuePanel = shell.querySelector('#playbackPanel');
  const dividers = {
    sidebar: shell.querySelector('#sidebarDivider'),
    queue: shell.querySelector('#queueDivider'),
  };
  const desktop = window.matchMedia('(min-width: 761px)');
  const wide = window.matchMedia('(min-width: 1120px)');
  const storageKey = 'music-report-panel-widths';
  let preferred = {};
  let widths;
  try {
    const saved = JSON.parse(localStorage.getItem(storageKey) || '{}') || {};
    for (const pane of Object.keys(dividers)) {
      if (Number.isFinite(saved[pane]) && saved[pane] > 0) preferred[pane] = saved[pane];
    }
  } catch {
    // Widths still work for the current page.
  }

  function renderWidths() {
    const collapsed = shell.classList.contains('is-sidebar-collapsed');
    const docked = wide.matches && !queuePanel.hidden;
    const css = getComputedStyle(shell);
    const defaultSidebar = parseFloat(css.getPropertyValue('--sidebar-default-width'));
    const defaultQueue = Math.max(280, Math.min(360, Math.round(window.innerWidth * .24)));
    widths = fitReportPanels(shell.clientWidth,
      parseFloat(css.getPropertyValue('--panel-gap')),
      preferred.sidebar ?? defaultSidebar, preferred.queue ?? defaultQueue, collapsed, docked);
    shell.style.setProperty('--sidebar-resized', widths.sidebar + 'px');
    shell.style.setProperty('--queue-resized', widths.queue ? widths.queue + 'px' : '');
    dividers.sidebar.hidden = !desktop.matches || collapsed;
    dividers.queue.hidden = !docked;
    for (const [pane, divider] of Object.entries(dividers)) {
      if (divider.hidden) continue;
      const neighbour = pane === 'sidebar' ? widths.queue : widths.sidebar;
      divider.setAttribute('aria-valuemin', String(reportPaneWidths[pane].min));
      divider.setAttribute('aria-valuemax', String(reportPaneMaximum(pane, widths.space, neighbour)));
      divider.setAttribute('aria-valuenow', String(widths[pane]));
      divider.setAttribute('aria-valuetext', widths[pane] + ' пикс.');
    }
  }

  function saveWidths() {
    try {
      localStorage.setItem(storageKey, JSON.stringify(preferred));
    } catch {
      // Widths still work for the current page.
    }
  }

  for (const [pane, divider] of Object.entries(dividers)) {
    const direction = pane === 'sidebar' ? 1 : -1;
    const neighbour = pane === 'sidebar' ? 'queue' : 'sidebar';
    let drag = null;

    function setWidth(requested) {
      if (divider.hidden) return false;
      const width = Math.max(reportPaneWidths[pane].min,
        Math.min(Math.round(requested), reportPaneMaximum(pane, widths.space, widths[neighbour])));
      if (width === widths[pane]) return false;
      if (!dividers[neighbour].hidden) preferred[neighbour] = widths[neighbour];
      preferred[pane] = width;
      renderWidths();
      return true;
    }

    divider.addEventListener('pointerdown', event => {
      if (drag || event.button !== 0 || event.isPrimary === false) return;
      drag = {id: event.pointerId, x: event.clientX, width: widths[pane], changed: false};
      divider.setPointerCapture(event.pointerId);
      divider.classList.add('is-dragging');
      divider.focus({preventScroll: true});
      event.preventDefault();
    });
    divider.addEventListener('pointermove', event => {
      if (drag?.id !== event.pointerId) return;
      if (setWidth(drag.width + direction * (event.clientX - drag.x))) drag.changed = true;
    });
    divider.addEventListener('lostpointercapture', event => {
      if (drag?.id !== event.pointerId) return;
      if (drag.changed) saveWidths();
      drag = null;
      divider.classList.remove('is-dragging');
    });
    divider.addEventListener('keydown', event => {
      let width = widths[pane];
      if (event.key === 'Home') width = reportPaneWidths[pane].min;
      else if (event.key === 'End') width = reportPaneMaximum(pane, widths.space, widths[neighbour]);
      else if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
        width += (event.key === 'ArrowRight' ? 1 : -1) * direction * (event.shiftKey ? 40 : 16);
      } else return;
      event.preventDefault();
      if (setWidth(width)) saveWidths();
    });
  }
  const observer = new MutationObserver(renderWidths);
  observer.observe(shell, {attributeFilter: ['class']});
  observer.observe(queuePanel, {attributeFilter: ['hidden']});
  window.addEventListener('resize', renderWidths);
  renderWidths();
}
"""


REPORT_CONTROLS_JS = r"""
(() => {
  document.querySelectorAll('.page-actions').forEach(menu => {
    const toggle = menu.querySelector('summary');
    function close(restoreFocus = false) {
      if (!menu.open) return;
      menu.open = false;
      if (restoreFocus) toggle.focus({preventScroll: true});
    }
    menu.addEventListener('click', event => {
      if (event.target.closest('.page-actions-panel button')) close(true);
    }, true);
    document.addEventListener('pointerdown', event => {
      if (!menu.contains(event.target)) close();
    });
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape') close(true);
    });
    window.addEventListener('report-page-change', () => close());
  });

  let closeCurrent = null;
  window.addEventListener('report-page-change', () => { if (closeCurrent) closeCurrent(); });
  document.querySelectorAll('.toolbar select, .playlist-sort select').forEach(select => {
    const customIcon = select.parentElement.querySelector('[data-select-icon]');
    const wrapper = document.createElement('div');
    wrapper.className = 'web-select';
    select.before(wrapper);
    wrapper.append(select);
    const trigger = document.createElement('button');
    trigger.type = 'button';
    trigger.className = 'web-select-trigger';
    trigger.id = select.id + '-trigger';
    trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-label', select.getAttribute('aria-label') || 'Выбрать');
    trigger.setAttribute('aria-haspopup', 'listbox');
    trigger.setAttribute('aria-expanded', 'false');
    trigger.setAttribute('aria-controls', select.id + '-options');
    const label = document.createElement('span');
    label.className = 'web-select-label';
    trigger.append(label);
    if (customIcon) {
      customIcon.removeAttribute('hidden');
      trigger.append(customIcon);
    } else {
      const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      arrow.setAttribute('viewBox', '0 0 24 24');
      arrow.setAttribute('aria-hidden', 'true');
      arrow.innerHTML = '<path d="m6 9 6 6 6-6"/>';
      trigger.append(arrow);
    }
    const menu = document.createElement('div');
    menu.className = 'web-select-menu';
    menu.id = select.id + '-options';
    menu.setAttribute('role', 'listbox');
    menu.setAttribute('aria-labelledby', trigger.id);
    menu.hidden = true;
    const scroller = document.createElement('div');
    scroller.className = 'web-select-options';
    menu.append(scroller);
    const supportsPopover = typeof menu.showPopover === 'function';
    if (supportsPopover) menu.setAttribute('popover', 'manual');
    wrapper.append(trigger, menu);
    const options = Array.from(select.options);
    let active = select.selectedIndex;
    let opened = false;
    let typeAhead = '';
    let lastTyped = 0;

    const items = options.map((option, index) => {
      const item = document.createElement('div');
      item.className = 'web-select-option';
      item.id = select.id + '-option-' + index;
      item.setAttribute('role', 'option');
      if (option.disabled) item.setAttribute('aria-disabled', 'true');
      item.textContent = option.textContent;
      item.title = option.textContent;
      item.addEventListener('pointermove', () => setActive(index));
      item.addEventListener('pointerdown', event => event.preventDefault());
      item.addEventListener('click', () => choose(index));
      scroller.append(item);
      return item;
    });

    function sync() {
      const selected = select.selectedOptions[0];
      label.textContent = selected?.dataset.label || selected?.textContent || '';
      trigger.disabled = select.disabled;
      items.forEach((item, index) => item.setAttribute('aria-selected', String(index === select.selectedIndex)));
    }
    function setActive(index, reveal = false) {
      if (!options[index] || options[index].disabled) return;
      active = index;
      items.forEach((item, i) => item.classList.toggle('active', i === index));
      trigger.setAttribute('aria-activedescendant', items[index].id);
      if (reveal) {
        const top = items[index].offsetTop - scroller.offsetTop;
        const bottom = top + items[index].offsetHeight;
        if (top < scroller.scrollTop) scroller.scrollTop = top;
        else if (bottom > scroller.scrollTop + scroller.clientHeight) scroller.scrollTop = bottom - scroller.clientHeight;
      }
    }
    function close(focus = false) {
      if (!opened) return;
      opened = false;
      if (supportsPopover && menu.matches(':popover-open')) menu.hidePopover();
      menu.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
      trigger.removeAttribute('aria-activedescendant');
      if (closeCurrent === close) closeCurrent = null;
      if (focus) trigger.focus({preventScroll: true});
    }
    function choose(index) {
      if (options[index].disabled) return;
      select.value = options[index].value;
      select.dispatchEvent(new Event('change', {bubbles: true}));
      sync();
      close(true);
    }
    function open() {
      if (opened || select.disabled) return;
      if (closeCurrent) closeCurrent();
      closeCurrent = close;
      opened = true;
      sync();
      const box = trigger.getBoundingClientRect();
      menu.style.width = Math.min(box.width, innerWidth - 24) + 'px';
      menu.style.maxHeight = '300px';
      menu.style.setProperty('--menu-height', '300px');
      menu.hidden = false;
      if (supportsPopover) menu.showPopover();
      const below = innerHeight - box.bottom - 20;
      const above = box.top - 20;
      const down = below >= Math.min(180, menu.scrollHeight) || below >= above;
      const maxHeight = Math.max(0, Math.min(300, down ? below : above)) + 'px';
      menu.style.maxHeight = maxHeight;
      menu.style.setProperty('--menu-height', maxHeight);
      const height = menu.getBoundingClientRect().height;
      const width = menu.getBoundingClientRect().width;
      const x = select.dataset.menuAlign === 'end' ? box.right - width : box.left;
      menu.style.left = Math.max(12, Math.min(x, innerWidth - width - 12)) + 'px';
      menu.style.top = (down ? box.bottom + 8 : box.top - height - 8) + 'px';
      trigger.setAttribute('aria-expanded', 'true');
      setActive(Math.max(0, select.selectedIndex), true);
    }
    function move(delta) {
      const enabled = options.map((option, i) => option.disabled ? -1 : i).filter(i => i >= 0);
      if (!enabled.length) return;
      const position = enabled.indexOf(active);
      setActive(enabled[(position + delta + enabled.length) % enabled.length], true);
    }
    trigger.addEventListener('click', () => opened ? close() : open());
    trigger.addEventListener('keydown', event => {
      if (event.key === 'Escape') { close(true); event.preventDefault(); return; }
      if (event.key === 'Tab') { close(); return; }
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        if (!opened) open(); else move(event.key === 'ArrowDown' ? 1 : -1);
      } else if (event.key === 'Home' || event.key === 'End') {
        event.preventDefault();
        if (!opened) open();
        const candidates = options.map((option, i) => option.disabled ? -1 : i).filter(i => i >= 0);
        if (candidates.length) setActive(event.key === 'Home' ? candidates[0] : candidates.at(-1), true);
      } else if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (!opened) open(); else choose(active);
      } else if (event.key.length === 1 && !event.ctrlKey && !event.altKey && !event.metaKey) {
        event.preventDefault();
        const now = Date.now();
        typeAhead = (now - lastTyped < 700 ? typeAhead : '') + event.key.toLocaleLowerCase('ru');
        lastTyped = now;
        if (!opened) open();
        const index = options.findIndex(option => !option.disabled && option.textContent.toLocaleLowerCase('ru').startsWith(typeAhead));
        if (index >= 0) setActive(index, true);
      }
    });
    document.addEventListener('pointerdown', event => { if (!wrapper.contains(event.target)) close(); });
    document.addEventListener('scroll', event => { if (!menu.contains(event.target)) close(); }, true);
    window.addEventListener('resize', () => close());
    select.addEventListener('change', sync);
    sync();
    select.hidden = true;
    select.tabIndex = -1;
  });

})();
"""
