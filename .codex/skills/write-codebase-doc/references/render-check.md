# Render-Check Mermaid Diagrams

Use the built-in browser. Mermaid is loaded from a pinned CDN build, so the page needs no local files.

1. Produce the blocks with `check_codebase_doc.py ... --mermaid-json <file>` and read the JSON array.
2. Open `https://cdn.jsdelivr.net/npm/mermaid@11.4.1/package.json`. Any page on that origin works; it
   only provides a context without a restrictive content security policy.
3. Run this in the page, with the JSON array pasted in place of `BLOCKS`:

   ```js
   const blocks = BLOCKS;
   const mermaid = (await import(
     'https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.esm.min.mjs')).default;
   mermaid.initialize({ startOnLoad: false });
   document.body.innerHTML = '';
   document.body.style.background = '#fff';
   const out = [];
   for (let i = 0; i < blocks.length; i++) {
     try {
       const { svg } = await mermaid.render('m' + i, blocks[i]);
       const div = document.createElement('div');
       div.id = 'd' + i;
       div.innerHTML = `<p>#${i}</p>` + svg;
       document.body.appendChild(div);
       out.push({ i, ok: true });
     } catch (e) {
       out.push({ i, ok: false, err: String(e.message || e).slice(0, 300) });
     }
   }
   out
   ```

   A block with `ok: false` has a syntax error; the message names the line.
4. Fit every diagram to the page width, which is roughly what a Markdown viewer does, then scroll each
   `#d<i>` into view and take a screenshot:

   ```js
   const w = document.documentElement.clientWidth - 30;
   document.querySelectorAll('svg').forEach(s => {
     s.style.maxWidth = w + 'px'; s.setAttribute('width', w); s.style.height = 'auto';
   });
   ```

   Keep the default viewport; an emulated wide viewport can be larger than the pane, and the
   screenshot then shows only part of the diagram. Judge the layout: crossing edges, nodes placed far
   from their group, edge labels cut short, and text too small because the diagram is much wider than
   it is tall. Node text slightly clipped at the box edge on this bare page comes from missing fonts
   and renders fine in real viewers.
5. To try a revised diagram, call `mermaid.render` again in the same page; the module stays loaded.
