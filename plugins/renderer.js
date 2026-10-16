/*  renderer.js - a minimal "data -> DOM" renderer

    Copyright (C) 2026, HomDGCat Wiki maintainers
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.
    See the GNU General Public License for more details.

    Contract: docs/renderer-contract.md (section 2.3)
    Goal: default HTML escaping, nested control flow, no build, self-contained.
    No virtual DOM / two-way binding by design.
*/

(function (global) {
    'use strict';

    /* ---------- utils ---------- */

    function isArray(v) { return Array.isArray(v); }

    function isPlainObject(v) {
        return Object.prototype.toString.call(v) === '[object Object]';
    }

    // HTML escape. Default path for all user/data strings.
    function escape(str) {
        if (str === undefined || str === null) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    // Resolve dotted path (a.b.c) from a root object. Returns undefined on miss.
    function getPath(obj, path) {
        if (path === '.' || path === '') return obj;
        var parts = path.split('.');
        var cur = obj;
        for (var i = 0; i < parts.length; i++) {
            if (cur == null) return undefined;
            cur = cur[parts[i]];
        }
        return cur;
    }

    // Resolve a field/value spec in a data context.
    //   value        literal  -> itself
    //   fn({data})            -> call result
    //   string "{{path}}"     -> escaped lookup (default)
    //   string "{{{path}}}"   -> raw lookup (explicit html)
    function resolve(spec, ctx) {
        if (typeof spec === 'function') {
            return resolve(spec(ctx), ctx);
        }
        if (typeof spec !== 'string') return spec;
        // {{path}} / {{{path}}} tokens
        var m;
        if ((m = /^\{\{\{(.+?)\}\}\}$/.exec(spec))) {
            return rawValue(getPath(ctx.data, m[1]));
        }
        if ((m = /^\{\{(.+?)\}\}$/.exec(spec))) {
            return escape(rawValue(getPath(ctx.data, m[1])));
        }
        return spec;
    }

    function rawValue(v) {
        return v === undefined || v === null ? '' : v;
    }

    // fill {{...}} / {{{...}}} inside an arbitrary string template
    function fill(template, ctx) {
        if (typeof template !== 'string') return template;
        return template.replace(/\{\{\{([^}]+)\}\}\}/g, function (m, p) {
            return rawValue(getPath(ctx.data, p.trim()));
        }).replace(/\{\{([^}]+)\}\}/g, function (m, p) {
            return escape(rawValue(getPath(ctx.data, p.trim())));
        });
    }

    /* ---------- element construction ---------- */

    function toDOM(html) {
        var tpl = document.createElement('template');
        tpl.innerHTML = html;
        // move all child nodes into a fragment
        var frag = document.createDocumentFragment();
        while (tpl.content.firstChild) {
            frag.appendChild(tpl.content.firstChild);
        }
        return frag;
    }

    // normalize content value(s) into an array of renderable items
    function itemsOf(content) {
        if (content === undefined || content === null) return [];
        return isArray(content) ? content : [content];
    }

    // append rendered children from a node's `t`
    function renderChildren(container, content, ctx) {
        itemsOf(content).forEach(function (item) {
            appendNode(container, item, ctx);
        });
    }

    function appendNode(container, template, ctx) {
        if (template === undefined || template === null) return;

        if (template instanceof Node) {
            container.appendChild(template);
            return;
        }

        if (typeof template === 'function') {
            var r = template(ctx);
            if (r == null) return;
            if (r instanceof Node) { container.appendChild(r); return; }
            container.appendChild(toDOM(fill(String(r), ctx)));
            return;
        }

        if (typeof template === 'string') {
            container.appendChild(toDOM(fill(template, ctx)));
            return;
        }

        if (isPlainObject(template)) {
            renderNode(container, template, ctx);
            return;
        }

        // array treated as siblings
        renderChildren(container, template, ctx);
    }

    // handle when / foreach / if / switch control on a node template, else plain element
    function renderNode(container, node, ctx) {
        // when - skip node if falsy
        if (node.hasOwnProperty('when')) {
            var w = node.when;
            var pass = typeof w === 'function' ? !!w({ data: ctx.data }) : !!w;
            if (!pass) return;
        }

        // if - conditional (nested-capable)
        if (node.hasOwnProperty('if')) {
            var iv = node.if;
            var cond = typeof iv === 'function' ? !!iv({ data: ctx.data }) : !!iv;
            var branch = cond ? (node.then || []) : (node.else || []);
            renderChildren(container, branch, ctx);
            return;
        }

        // switch - branch by case
        if (node.hasOwnProperty('switch')) {
            var sv = node.switch;
            var key = typeof sv === 'function' ? sv({ data: ctx.data }) : sv;
            var rt = node.case && node.case.hasOwnProperty(key)
                ? node.case[key]
                : (node.default || []);
            renderChildren(container, rt, ctx);
            return;
        }

        // foreach - iterate over provided array (nested-capable)
        if (node.hasOwnProperty('foreach')) {
            var src = node.foreach;
            var arr = typeof src === 'function' ? src({ data: ctx.data }) : src;
            (arr || []).forEach(function (item, i) {
                var childCtx = { data: item, parent: ctx.data, index: i };
                renderChildren(container, node.t, childCtx);
            });
            return;
        }

        // plain element node
        var e = document.createElement(node.e || 'div');

        if (node.id !== undefined) e.id = node.id;
        if (node.name !== undefined) e.setAttribute('name', node.name);
        if (node.class !== undefined) e.className = node.class;

        if (node.a) {
            Object.keys(node.a).forEach(function (k) {
                var v = node.a[k];
                var val = resolve(v, ctx);
                if (val !== undefined && val !== null) e.setAttribute(k, val);
            });
        }

        if (node.style) {
            Object.keys(node.style).forEach(function (k) {
                var v = node.style[k];
                var val = typeof v === 'function' ? v({ data: ctx.data }) : v;
                if (val === undefined || val === null) return;
                e.style[k] = String(val);
            });
        }

        if (node.text !== undefined) {
            e.textContent = resolve(node.text, ctx);
        }

        renderChildren(e, node.t, ctx);

        // set value on form fields after children (so select options exist)
        if (node.value !== undefined) {
            var vv = typeof node.value === 'function' ? node.value({ data: ctx.data }) : node.value;
            e.value = vv === undefined || vv === null ? '' : vv;
        }

        container.appendChild(e);
    }

    /* ---------- public API ---------- */

    function render(container, template, data) {
        var el = typeof container === 'string'
            ? document.querySelector(container)
            : container;
        if (!el) return;

        el.innerHTML = '';

        var ctx = { data: data || {} };
        // array as the whole template -> list over the data array
        if (isArray(template)) {
            var arr = isArray(data) ? data : [data];
            arr.forEach(function (item) {
                renderChildren(el, template, { data: item });
            });
        } else {
            renderChildren(el, template, ctx);
        }
        return el;
    }

    var X = {
        render: render,
        escape: escape,
        fill: fill,
        getPath: getPath
    };

    global.X = X;
})(typeof window !== 'undefined' ? window : this);