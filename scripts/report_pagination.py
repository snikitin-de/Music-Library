"""Incremental mounting of standalone report cards, ten items at a time."""

REPORT_PAGINATION_JS = r"""
class ReportPagedList {
  constructor(container, panel, page, onMount) {
    this.container = container;
    this.panel = panel;
    this.page = page;
    this.onMount = onMount;
    this.items = [];
    this.limit = 10;
    this.started = false;
    this.button = panel.querySelector('button');
    this.count = panel.querySelector('[role="status"]');
    this.button.addEventListener('click', () => this.more());
    if ('IntersectionObserver' in window) {
      this.observer = new IntersectionObserver(entries => {
        if (entries.some(entry => entry.isIntersecting)) this.more();
      }, {rootMargin: '200px 0px'});
      this.observer.observe(this.button);
    }
  }

  setItems(items, reset = true) {
    this.items = items;
    if (reset) this.limit = 10;
    if (this.started) this.render();
  }

  activate() {
    if (!this.started) {
      this.started = true;
      this.render();
    }
  }

  more() {
    if (!this.started || this.page.hidden || this.limit >= this.items.length) return;
    this.limit += 10;
    this.render();
  }

  render() {
    const next = this.items.slice(0, this.limit);
    const wanted = new Set(next);
    Array.from(this.container.children).forEach(card => {
      if (!wanted.has(card)) {
        card.querySelectorAll('audio').forEach(player => player.pause());
        card.remove();
      }
    });
    next.forEach((card, index) => {
      if (this.container.children[index] !== card) {
        this.container.insertBefore(card, this.container.children[index] || null);
      }
      this.onMount(card);
    });
    this.panel.hidden = this.items.length === 0;
    this.button.hidden = next.length === this.items.length;
    this.count.textContent = 'Показано ' + next.length.toLocaleString('ru-RU') + ' из ' + this.items.length.toLocaleString('ru-RU');
  }
}
"""
