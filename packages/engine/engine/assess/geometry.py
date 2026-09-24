"""Where everything prints: the record the renderer writes beside each PDF (`render_sheet` → `<id>.key.json`,
`geometry`), one entry per answer cell, tick, text box and working space, in millimetres from the page's
top-left corner. Pure: the marker (`assess/mark.py`) and the box reader (`w3_read/boxes.py`) read a scan by it,
so a paper says where its answers live and nothing has to search for them (rule 1)."""

# Run in the page as the browser laid it out, before it is printed to PDF: the browser's own pixel rectangles
# are the only true record of where a cell landed after every line wrapped.
GEOM_JS = """
() => {
  const mm = 25.4/96;
  const pages=[...document.querySelectorAll('.page')]; const out=[];
  pages.forEach((pg,pi)=>{
    const pr=pg.getBoundingClientRect();
    pg.querySelectorAll('[data-r]').forEach(el=>{
      const r=el.getBoundingClientRect();
      out.push({page:pi+1, item:el.dataset.i, resp:el.dataset.r, k:+el.dataset.k, opt:el.dataset.opt||null,
        kind: el.classList.contains('tick')?'tick':(el.classList.contains('textbox')?'text':'digit'),
        x:(r.left-pr.left)*mm, y:(r.top-pr.top)*mm, w:r.width*mm, h:r.height*mm});
    });
    // the working space of each question: recorded so a scan can say it was written in (rule 5's third
    // signal) and so nothing in it is ever read as the answer
    pg.querySelectorAll('.work').forEach(el=>{
      const it=el.closest('.item'); if(!it) return;
      const r=el.getBoundingClientRect();
      out.push({page:pi+1, item:it.dataset.item, resp:null, k:0, opt:null, kind:'work',
        x:(r.left-pr.left)*mm, y:(r.top-pr.top)*mm, w:r.width*mm, h:r.height*mm});
    });
  });
  return {pages: pages.length, cells: out};
}
"""


def cells_of(geometry, page_no):
    """{(item_key, rid): [its digit cells in order]}, {item_key: [its working spaces]} for one page."""
    runs, works = {}, {}
    for g in geometry:
        if g["page"] != page_no:
            continue
        if g.get("kind") == "work":
            works.setdefault(g["item"], []).append(g)
        elif g.get("kind") == "digit":
            runs.setdefault((g["item"], g["resp"]), []).append(g)
    return {k: sorted(v, key=lambda c: c["k"]) for k, v in runs.items()}, works
