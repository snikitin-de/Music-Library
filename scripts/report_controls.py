"""Progressive enhancement for standalone report controls and chart rendering."""

REPORT_CONTROLS_JS = r"""
(() => {
  let closeCurrent = null;
  document.querySelectorAll('.toolbar select').forEach(select => {
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
    const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    arrow.setAttribute('viewBox', '0 0 24 24');
    arrow.setAttribute('aria-hidden', 'true');
    arrow.innerHTML = '<path d="m6 9 6 6 6-6"/>';
    trigger.append(arrow);
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
      item.addEventListener('pointermove', () => setActive(index));
      item.addEventListener('pointerdown', event => event.preventDefault());
      item.addEventListener('click', () => choose(index));
      scroller.append(item);
      return item;
    });

    function sync() {
      label.textContent = select.selectedOptions[0]?.textContent || '';
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
      menu.style.width = Math.min(Math.max(box.width, 240), innerWidth - 24) + 'px';
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
      menu.style.left = Math.max(12, Math.min(box.left, innerWidth - menu.getBoundingClientRect().width - 12)) + 'px';
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

  // Draw at four times the physical pixel density; CSS downsamples the ring.
  // SVG stays in the standalone document as a no-canvas fallback.
  document.querySelectorAll('.donut-chart').forEach(chart => {
    const svg = chart.querySelector('.donut-svg');
    if (!svg) return;
    const canvas = document.createElement('canvas');
    canvas.className = 'donut-canvas';
    canvas.setAttribute('aria-hidden', 'true');
    const context = canvas.getContext('2d');
    if (!context) return;
    chart.insertBefore(canvas, svg);
    let lastSize = '';
    function draw() {
      const box = chart.getBoundingClientRect();
      const ratio = 4 * Math.max(1, Math.min(devicePixelRatio || 1, 3));
      const width = Math.round(box.width * ratio);
      const height = Math.round(box.height * ratio);
      if (!width || !height || lastSize === width + ':' + height) return;
      lastSize = width + ':' + height;
      canvas.width = width;
      canvas.height = height;
      context.scale(width / 100, height / 100);
      context.lineWidth = 21;
      context.lineCap = 'butt';
      svg.querySelectorAll('.donut-segment').forEach(segment => {
        const length = parseFloat(segment.getAttribute('stroke-dasharray'));
        const start = -parseFloat(segment.getAttribute('stroke-dashoffset'));
        context.strokeStyle = segment.getAttribute('stroke');
        context.beginPath();
        context.arc(50, 50, 35.5, start / 100 * Math.PI * 2 - Math.PI / 2, (start + length) / 100 * Math.PI * 2 - Math.PI / 2);
        context.stroke();
      });
      svg.style.visibility = 'hidden';
    }
    draw();
    if (typeof ResizeObserver === 'function') new ResizeObserver(draw).observe(chart);
    window.addEventListener('resize', draw);
  });
})();
"""
