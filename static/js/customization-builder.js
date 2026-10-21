/**
 * CraftX3D — Field Customization Builder v2
 * Fixed: event listener accumulation, class field compatibility
 */
(function() {
'use strict';

// ── CSS ──────────────────────────────────────────────────
var style = document.createElement('style');
style.textContent = [
'.cb-wrap{display:flex;flex-direction:column;gap:12px}',
'.cb-card{background:#fff;border:1.5px solid var(--m-border,#E5E7EB);border-radius:12px;overflow:hidden}',
'.cb-header-card{padding:20px}',
'.cb-section-card{transition:box-shadow 0.2s;cursor:grab}',
'.cb-section-card.cb-dragging{opacity:0.5;box-shadow:0 0 0 2px var(--m-accent,#F5A623)}',
'.cb-section-card.cb-drag-over{box-shadow:0 0 0 3px var(--m-accent,#F5A623)}',
'.cb-section-header{display:flex;align-items:center;gap:10px;padding:14px 16px;user-select:none}',
'.cb-drag-handle{color:#9CA3AF;font-size:1rem;flex-shrink:0}',
'.cb-section-label{font-weight:700;font-size:0.88rem;flex:1}',
'.cb-expand-btn{background:#F3F4F6;border:1.5px solid #E5E7EB;border-radius:6px;padding:3px 8px;cursor:pointer;font-size:0.72rem;color:#6B7280}',
'.cb-section-body{display:none;padding:16px 20px;border-top:1px solid #E5E7EB;flex-direction:column;gap:14px}',
'.cb-section-body.cb-open{display:flex}',
'.cb-field-row{display:flex;flex-direction:column;gap:6px}',
'.cb-label{font-size:0.82rem;font-weight:600;color:#1C1C2E}',
'.cb-label-sm{font-size:0.75rem;font-weight:600;color:#6B7280;margin-bottom:4px;display:block}',
'.cb-row{display:flex;gap:16px;align-items:flex-start}',
'.cb-order-hint{font-size:0.75rem;color:#9CA3AF;margin-top:12px;background:#F9FAFB;border-radius:6px;padding:8px 10px}',
'.cb-item-row{display:flex;align-items:flex-start;gap:10px;padding:10px 12px;background:#F9FAFB;border-radius:8px;margin-bottom:8px}',
'.cb-item-header{font-weight:700;font-size:0.82rem;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between}',
'.cb-item-num{min-width:22px;height:22px;background:#6B7280;color:#fff;border-radius:50%;font-size:0.65rem;font-weight:800;display:flex;align-items:center;justify-content:center;flex-shrink:0;margin-top:8px}',
'.cb-remove-btn{background:none;border:none;color:#EF4444;cursor:pointer;font-size:0.9rem;padding:4px 6px;flex-shrink:0;margin-top:4px}',
'.cb-remove-btn-inline{background:#EF4444;color:#fff;border:none;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:0.7rem}',
'.cb-add-btn{padding:8px 14px;background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:8px;font-size:0.8rem;color:#9CA3AF;cursor:pointer;transition:all 0.2s;margin-top:4px;width:auto;display:inline-block}',
'.cb-add-btn:hover{border-color:#F5A623;color:#F5A623}',
'.cb-add-btn-sm{padding:5px 10px;background:#F9FAFB;border:1.5px dashed #E5E7EB;border-radius:6px;font-size:0.75rem;color:#9CA3AF;cursor:pointer;margin-top:6px;display:inline-block}',
'.cb-add-btn-sm:hover{border-color:#F5A623;color:#F5A623}',
'.cb-field-grid{display:grid;grid-template-columns:1fr 110px 1fr auto;gap:8px;flex:1}',
'.cb-field-grid-4{display:grid;grid-template-columns:1fr 80px 90px 80px;gap:8px;flex:1}',
'.cb-combo-field-grid{display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:10px;flex:1}',
'.cb-inline-label{display:flex;align-items:center;gap:6px;font-size:0.82rem;white-space:nowrap;margin-top:8px}',
'.cb-color-input{width:36px;height:32px;border:1.5px solid #E5E7EB;border-radius:6px;cursor:pointer;padding:2px}',
'.cb-color-preview{width:26px;height:26px;border-radius:6px;border:1.5px solid #E5E7EB;flex-shrink:0;display:inline-block;margin-left:4px;vertical-align:middle}',
'.cb-tc-slot{border:1px solid #E5E7EB;border-radius:8px;padding:14px;margin-bottom:10px}',
'.cb-tc-header{font-weight:700;font-size:0.85rem;margin-bottom:10px;color:#1C1C2E}',
'.cb-info-box{background:#FFF7ED;border-left:3px solid #F5A623;border-radius:0 8px 8px 0;padding:10px 14px;font-size:0.78rem;color:#92400E}',
'.cb-radio{display:flex;align-items:center;gap:6px;font-size:0.85rem;cursor:pointer}',
'.cb-slots-list{display:flex;flex-direction:column}',
'.cb-combo-row{align-items:flex-start;flex-direction:column}',
'@media(max-width:640px){.cb-field-grid{grid-template-columns:1fr}.cb-field-grid-4{grid-template-columns:1fr 1fr}.cb-combo-field-grid{grid-template-columns:1fr}}'
].join('');
document.head.appendChild(style);

// ── SECTION META ─────────────────────────────────────────
var SECTION_META = {
  photo:          { icon:'📸', label:'Photo Upload' },
  text_fields:    { icon:'📝', label:'Text Input Fields' },
  select_model:   { icon:'🎭', label:'Select the Model (Dropdown)' },
  colour_combos:  { icon:'🎨', label:'Choose the Colour (Dual-colour combos)' },
  text_colours:   { icon:'✏️', label:'Text Colour (6 named colour sets)' },
  size_options:   { icon:'📐', label:'Size Options' },
  pack_options:   { icon:'📦', label:'Pack Size Options' },
  suggestion_box: { icon:'💬', label:'Suggestion Box' },
  personalisation:{ icon:'✏️', label:'Personalisation' },
};

// ── BUILDER CLASS ─────────────────────────────────────────
function CustomizationBuilder(containerId, hiddenInputId, initialData) {
  this.container = document.getElementById(containerId);
  this.hiddenInput = document.getElementById(hiddenInputId);
  // Robustly merge initialData with defaults — prevents crash when {} or partial data passed
  this.state = this._mergeWithDefaults(initialData);
  this._listeners = [];
  if (this.container) {
    this.render();
    this._sync();
  }
}

CustomizationBuilder.prototype._mergeWithDefaults = function(initialData) {
  var def = this._defaultState();
  // Guard: if no data, or not an object, or missing critical keys → use defaults
  if (!initialData || typeof initialData !== 'object') return def;
  if (!initialData.sections || typeof initialData.sections !== 'object') return def;
  if (!Array.isArray(initialData.section_order) || initialData.section_order.length === 0) return def;

  var merged = {
    card_title:    initialData.card_title    !== undefined ? initialData.card_title    : def.card_title,
    show_header:   initialData.show_header   !== undefined ? initialData.show_header   : def.show_header,
    section_order: initialData.section_order,
    sections: {}
  };

  // For each section, merge saved data over defaults so nothing is undefined
  def.section_order.forEach(function(key) {
    var saved = initialData.sections[key];
    var dflt  = def.sections[key];
    if (saved && typeof saved === 'object') {
      // Shallow merge: saved values win, but defaults fill in any missing keys
      merged.sections[key] = Object.assign({}, dflt, saved);
    } else {
      merged.sections[key] = dflt;
    }
  });

  return merged;
};

CustomizationBuilder.prototype._defaultState = function() {
  return {
    card_title: 'Customise Your Order',
    show_header: true,
    section_order: ['photo','text_fields','select_model','colour_combos','text_colours','size_options','pack_options','suggestion_box','personalisation'],
    sections: {
      photo:          { enabled: false, title: '📸 Upload Your Photos', slots: [] },
      text_fields:    { enabled: false, fields: [] },
      select_model:   { enabled: false, title: 'Select the Model', options: [] },
      colour_combos:  { enabled: false, title: 'Choose the Colour', combos: [] },
      text_colours:   { enabled: false, title: 'Text Colour', slots: this._makeTextColourSlots() },
      size_options:   { enabled: false, title: 'Select Size', sizes: [] },
      pack_options:   { enabled: false, packs: [] },
      suggestion_box: { enabled: false, title: 'Special Instructions', max_chars: 500 },
      personalisation:{ enabled: false, title: 'Personalise', pricing:'free', extra_price:0, fonts:[], sizes:[], max_chars_per_line:20, max_lines:3 },
    }
  };
};

CustomizationBuilder.prototype._makeTextColourSlots = function() {
  var slots = [];
  for (var i = 0; i < 6; i++) slots.push({ title: 'Text Colour ' + (i+1), colours: [] });
  return slots;
};

CustomizationBuilder.prototype._sync = function() {
  if (this.hiddenInput) this.hiddenInput.value = JSON.stringify(this.state);
};

CustomizationBuilder.prototype._esc = function(str) {
  return String(str || '').replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
};

// ── RENDER ────────────────────────────────────────────────
CustomizationBuilder.prototype.render = function() {
  if (!this.container) return;
  // Clear all old listeners
  this._listeners.forEach(function(l) {
    if (l.el && l.el.removeEventListener) l.el.removeEventListener(l.type, l.fn);
  });
  this._listeners = [];

  var s = this.state;
  var html = '<div class="cb-wrap">';
  // Header card
  html += '<div class="cb-card cb-header-card">';
  html += '<div class="cb-row">';
  html += '<div style="flex:1"><label class="cb-label">Card Title <span style="color:#9CA3AF;font-weight:400">(shown to customer)</span></label>';
  html += '<input type="text" class="m-field" id="cbCardTitle" value="' + this._esc(s.card_title) + '" placeholder="e.g. Customise Your Order" style="margin-top:6px"></div>';
  html += '<div><label class="cb-label" style="margin-bottom:8px;display:block">Show Header</label>';
  html += '<div class="toggle-switch"><input type="checkbox" class="toggle-input" id="cbShowHeader"' + (s.show_header ? ' checked' : '') + '>';
  html += '<label class="toggle-track" for="cbShowHeader"></label></div></div></div>';
  html += '<div class="cb-order-hint">☰ Drag sections below to reorder them for customers</div></div>';

  // Section cards
  html += '<div id="cbOrderList">';
  var self = this;
  s.section_order.forEach(function(key) {
    html += self._renderSection(key);
  });
  html += '</div></div>';

  this.container.innerHTML = html;
  this._attachEvents();
  this._initDrag();
};

CustomizationBuilder.prototype._renderSection = function(key) {
  var meta = SECTION_META[key];
  var sec = this.state.sections[key];
  var isOn = sec.enabled;
  return '<div class="cb-card cb-section-card" data-key="' + key + '" draggable="true">' +
    '<div class="cb-section-header">' +
      '<span class="cb-drag-handle">☰</span>' +
      '<span>' + meta.icon + '</span>' +
      '<span class="cb-section-label">' + meta.label + '</span>' +
      '<div style="display:flex;align-items:center;gap:10px;margin-left:auto">' +
        '<div class="toggle-switch">' +
          '<input type="checkbox" class="toggle-input cb-section-toggle" id="cbTog-' + key + '" data-key="' + key + '"' + (isOn ? ' checked' : '') + '>' +
          '<label class="toggle-track" for="cbTog-' + key + '"></label>' +
        '</div>' +
        '<button type="button" class="cb-expand-btn" data-key="' + key + '">' + (isOn ? '▲' : '▼') + '</button>' +
      '</div>' +
    '</div>' +
    '<div class="cb-section-body' + (isOn ? ' cb-open' : '') + '" id="cbBody-' + key + '">' +
      '<div class="cb-field-row" style="margin-bottom:2px;"><label class="cb-label-sm">Step Subtitle <span style="font-weight:400;color:#9CA3AF;">(shown under the title on the customer\'s step page — optional)</span></label>' +
      '<input type="text" class="m-field" data-bind="' + key + '.subtitle" value="' + this._esc(sec.subtitle || '') + '" placeholder="e.g. Choose the base colour for your lamp\'s stand and the glow tone."></div>' +
      this._renderSectionBody(key) +
    '</div>' +
  '</div>';
};

CustomizationBuilder.prototype._renderSectionBody = function(key) {
  var s = this.state.sections;
  switch(key) {
    case 'photo': return this._renderPhoto(s.photo);
    case 'text_fields': return this._renderTextFields(s.text_fields);
    case 'select_model': return this._renderSelectModel(s.select_model);
    case 'colour_combos': return this._renderColourCombos(s.colour_combos);
    case 'text_colours': return this._renderTextColours(s.text_colours);
    case 'size_options': return this._renderSizeOptions(s.size_options);
    case 'pack_options': return this._renderPackOptions(s.pack_options);
    case 'suggestion_box': return this._renderSuggestionBox(s.suggestion_box);
    case 'personalisation': return this._renderPersonalisation(s.personalisation);
    default: return '';
  }
};

// ── SECTION RENDERERS ──────────────────────────────────────
CustomizationBuilder.prototype._renderPhoto = function(s) {
  var rows = (s.slots||[]).map(function(sl,i) {
    return '<div class="cb-item-row"><span class="cb-item-num">'+(i+1)+'</span>' +
      '<div style="flex:1;display:grid;grid-template-columns:1fr auto;gap:8px;align-items:center">' +
        '<input type="text" class="m-field" data-bind="photo.slots.'+i+'.label" value="' + this._esc(sl.label) + '" placeholder="Slot label (e.g. Front photo)">' +
        '<label class="cb-inline-label" style="margin:0"><input type="checkbox" data-bind="photo.slots.'+i+'.required"' + (sl.required?' checked':'') + '> Required</label>' +
      '</div>' +
      '<button type="button" class="cb-remove-btn" data-action="remove-photo-slot" data-idx="'+i+'">✕</button></div>';
  }, this).join('');
  return '<div class="cb-field-row"><label class="cb-label">Section Title</label>' +
    '<input type="text" class="m-field" data-bind="photo.title" value="' + this._esc(s.title||'') + '" placeholder="e.g. Upload Your Photos"></div>' +
    rows + '<button type="button" class="cb-add-btn" data-action="add-photo-slot">+ Add Slot</button>';
};

CustomizationBuilder.prototype._renderTextFields = function(s) {
  var rows = (s.fields||[]).map(function(f,i) {
    return '<div class="cb-item-row" style="flex-wrap:nowrap"><span class="cb-item-num">'+(i+1)+'</span>' +
      '<div class="cb-field-grid" style="flex:1">' +
        '<div><label class="cb-label-sm">Field Label *</label><input type="text" class="m-field" data-bind="text_fields.fields.'+i+'.label" value="' + this._esc(f.label||'') + '" placeholder="e.g. Name"></div>' +
        '<div><label class="cb-label-sm">Max Chars</label><input type="number" class="m-field" data-bind="text_fields.fields.'+i+'.max_chars" value="' + (f.max_chars||50) + '" min="1"></div>' +
        '<div><label class="cb-label-sm">Placeholder</label><input type="text" class="m-field" data-bind="text_fields.fields.'+i+'.placeholder" value="' + this._esc(f.placeholder||'') + '" placeholder="Example shown to customer"></div>' +
        '<div style="padding-top:20px"><label class="cb-inline-label" style="margin:0"><input type="checkbox" data-bind="text_fields.fields.'+i+'.required"' + (f.required?' checked':'') + '> Required</label></div>' +
      '</div>' +
      '<button type="button" class="cb-remove-btn" data-action="remove-text-field" data-idx="'+i+'">✕</button></div>';
  }, this).join('');
  return rows + '<button type="button" class="cb-add-btn" data-action="add-text-field">+ Add Field</button>';
};

CustomizationBuilder.prototype._renderSelectModel = function(s) {
  var rows = (s.options||[]).map(function(o,i) {
    return '<div class="cb-item-row"><span class="cb-item-num">'+(i+1)+'</span>' +
      '<input type="text" class="m-field" data-bind="select_model.options.'+i+'" value="' + this._esc(o||'') + '" placeholder="e.g. Flower">' +
      '<button type="button" class="cb-remove-btn" data-action="remove-model-option" data-idx="'+i+'">✕</button></div>';
  }, this).join('');
  return '<div class="cb-field-row"><label class="cb-label">Section Title</label>' +
    '<input type="text" class="m-field" data-bind="select_model.title" value="' + this._esc(s.title||'') + '"></div>' +
    rows + '<button type="button" class="cb-add-btn" data-action="add-model-option">+ Add Option</button>';
};

CustomizationBuilder.prototype._renderColourCombos = function(s) {
  var rows = (s.combos||[]).map(function(c,i) {
    return '<div class="cb-item-row cb-combo-row">' +
      '<div style="flex:1"><div class="cb-item-header">Combo '+(i+1)+' <button type="button" class="cb-remove-btn-inline" data-action="remove-colour-combo" data-idx="'+i+'">✕</button></div>' +
      '<div class="cb-combo-field-grid">' +
        '<div><label class="cb-label-sm">Colour 1 *</label><div style="display:flex;align-items:center;gap:4px"><input type="color" class="cb-color-input" data-bind="colour_combos.combos.'+i+'.color1" value="' + (c.color1||'#FF6600') + '"><span class="cb-color-preview" style="background:' + (c.color1||'#FF6600') + '"></span><input type="text" class="m-field" data-bind="colour_combos.combos.'+i+'.color1_name" value="' + this._esc(c.color1_name||'') + '" placeholder="e.g. Orange"></div></div>' +
        '<div><label class="cb-label-sm">Colour 2 *</label><div style="display:flex;align-items:center;gap:4px"><input type="color" class="cb-color-input" data-bind="colour_combos.combos.'+i+'.color2" value="' + (c.color2||'#000000') + '"><span class="cb-color-preview" style="background:' + (c.color2||'#000000') + '"></span><input type="text" class="m-field" data-bind="colour_combos.combos.'+i+'.color2_name" value="' + this._esc(c.color2_name||'') + '" placeholder="e.g. Black"></div></div>' +
        '<div><label class="cb-label-sm">Description</label><input type="text" class="m-field" data-bind="colour_combos.combos.'+i+'.description" value="' + this._esc(c.description||'') + '" placeholder="optional"></div>' +
        '<div style="font-size:.72rem;color:#9CA3AF;align-self:end;padding-bottom:8px;">Shown as: <strong>' + this._esc((c.color1_name||'Colour 1') + ' / ' + (c.color2_name||'Colour 2')) + '</strong></div>' +
      '</div></div></div>';
  }, this).join('');
  return '<div class="cb-field-row"><label class="cb-label">Section Title</label>' +
    '<input type="text" class="m-field" data-bind="colour_combos.title" value="' + this._esc(s.title||'') + '"></div>' +
    rows + '<button type="button" class="cb-add-btn" data-action="add-colour-combo">+ Add Combo</button>';
};

CustomizationBuilder.prototype._renderTextColours = function(s) {
  var slots = s.slots || this._makeTextColourSlots();
  var html = '<div class="cb-field-row"><label class="cb-label">Overall Section Title</label>' +
    '<input type="text" class="m-field" data-bind="text_colours.title" value="' + this._esc(s.title||'Text Colour') + '"></div>';
  slots.forEach(function(sl,i) {
    html += '<div class="cb-tc-slot">';
    html += '<div class="cb-tc-header">🖊️ Text Colour ' + (i+1) + '</div>';
    html += '<div class="cb-field-row"><label class="cb-label-sm">Title for this colour slot</label>';
    html += '<input type="text" class="m-field" data-bind="text_colours.slots.'+i+'.title" value="' + this._esc(sl.title||'') + '" placeholder="e.g. Main Text Colour"></div>';
    (sl.colours||[]).forEach(function(col,j) {
      html += '<div class="cb-item-row">' +
        '<input type="text" class="m-field" data-bind="text_colours.slots.'+i+'.colours.'+j+'.name" value="' + this._esc(col.name||'') + '" placeholder="Colour name">' +
        '<div style="display:flex;align-items:center;gap:4px"><input type="color" class="cb-color-input" data-bind="text_colours.slots.'+i+'.colours.'+j+'.hex" value="' + (col.hex||'#000000') + '"><span class="cb-color-preview" style="background:' + (col.hex||'#000000') + '"></span></div>' +
        '<button type="button" class="cb-remove-btn" data-action="remove-tc-colour" data-slot="'+i+'" data-idx="'+j+'">✕</button></div>';
    }, this);
    html += '<button type="button" class="cb-add-btn-sm" data-action="add-tc-colour" data-slot="'+i+'">+ Add Colour</button></div>';
  }, this);
  return html;
};

CustomizationBuilder.prototype._renderSizeOptions = function(s) {
  var rows = (s.sizes||[]).map(function(sz,i) {
    return '<div class="cb-item-row"><span class="cb-item-num">'+(i+1)+'</span>' +
      '<input type="text" class="m-field" data-bind="size_options.sizes.'+i+'.label" value="' + this._esc(sz.label||'') + '" placeholder="e.g. Small">' +
      '<div style="display:flex;align-items:center;gap:4px"><span style="font-size:0.8rem;color:#9CA3AF;white-space:nowrap">₹ Extra</span><input type="number" class="m-field" style="width:80px" data-bind="size_options.sizes.'+i+'.extra_price" value="' + (sz.extra_price||0) + '" min="0"></div>' +
      '<button type="button" class="cb-remove-btn" data-action="remove-size" data-idx="'+i+'">✕</button></div>';
  }, this).join('');
  return '<div class="cb-field-row"><label class="cb-label">Section Label</label>' +
    '<input type="text" class="m-field" data-bind="size_options.title" value="' + this._esc(s.title||'Select Size') + '"></div>' +
    rows + '<button type="button" class="cb-add-btn" data-action="add-size">+ Add Size</button>';
};

CustomizationBuilder.prototype._renderPackOptions = function(s) {
  var rows = (s.packs||[]).map(function(p,i) {
    return '<div class="cb-item-row cb-combo-row">' +
      '<div style="flex:1"><div class="cb-item-header">Pack '+(i+1)+' <button type="button" class="cb-remove-btn-inline" data-action="remove-pack" data-idx="'+i+'">✕</button></div>' +
      '<div class="cb-field-grid-4">' +
        '<div><label class="cb-label-sm">Label</label><input type="text" class="m-field" data-bind="pack_options.packs.'+i+'.label" value="' + this._esc(p.label||'') + '" placeholder="e.g. Buy 1"></div>' +
        '<div><label class="cb-label-sm">Min Qty</label><input type="number" class="m-field" data-bind="pack_options.packs.'+i+'.min_qty" value="' + (p.min_qty||1) + '" min="1"></div>' +
        '<div><label class="cb-label-sm">₹ Each</label><input type="number" class="m-field" data-bind="pack_options.packs.'+i+'.price" value="' + (p.price||'') + '" placeholder="299"></div>' +
        '<div><label class="cb-label-sm">% Off</label><input type="number" class="m-field" data-bind="pack_options.packs.'+i+'.discount_percent" value="' + (p.discount_percent||0) + '" min="0"></div>' +
      '</div></div></div>';
  }, this).join('');
  return rows + '<button type="button" class="cb-add-btn" data-action="add-pack">+ Add Pack</button>';
};

CustomizationBuilder.prototype._renderSuggestionBox = function(s) {
  return '<div class="cb-field-row"><label class="cb-label">Label shown to customer</label>' +
    '<input type="text" class="m-field" data-bind="suggestion_box.title" value="' + this._esc(s.title||'Special Instructions') + '"></div>' +
    '<div class="cb-field-row"><label class="cb-label">Max characters</label>' +
    '<input type="number" class="m-field" style="max-width:120px" data-bind="suggestion_box.max_chars" value="' + (s.max_chars||500) + '"></div>';
};

CustomizationBuilder.prototype._renderPersonalisation = function(s) {
  var fonts = (s.fonts||[]).map(function(f,i) {
    return '<div class="cb-item-row"><span class="cb-item-num">'+(i+1)+'</span>' +
      '<input type="text" class="m-field" data-bind="personalisation.fonts.'+i+'" value="' + this._esc(f||'') + '" placeholder="e.g. Script">' +
      '<button type="button" class="cb-remove-btn" data-action="remove-font" data-idx="'+i+'">✕</button></div>';
  }, this).join('');
  var sizes = (s.sizes||[]).map(function(sz,i) {
    return '<div class="cb-item-row"><span class="cb-item-num">'+(i+1)+'</span>' +
      '<input type="text" class="m-field" style="flex:1" data-bind="personalisation.sizes.'+i+'.label" value="' + this._esc(sz.label||'') + '" placeholder="e.g. Medium">' +
      '<div style="display:flex;align-items:center;gap:4px"><input type="number" class="m-field" style="width:76px" data-bind="personalisation.sizes.'+i+'.px" value="' + (sz.px||16) + '" min="6" max="120"><span style="font-size:0.78rem;color:#9CA3AF">px</span></div>' +
      '<button type="button" class="cb-remove-btn" data-action="remove-pers-size" data-idx="'+i+'">✕</button></div>';
  }, this).join('');
  return '<div class="cb-field-row"><label class="cb-label">Section Label</label>' +
    '<input type="text" class="m-field" data-bind="personalisation.title" value="' + this._esc(s.title||'Personalise') + '"></div>' +
    '<div class="cb-field-row"><label class="cb-label">Pricing</label>' +
    '<div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:4px">' +
      '<label class="cb-radio"><input type="radio" name="persPricing" value="free"' + (s.pricing==='free'?' checked':'') + '> FREE</label>' +
      '<label class="cb-radio"><input type="radio" name="persPricing" value="extra"' + (s.pricing==='extra'?' checked':'') + '> Extra Price' +
        ' <input type="number" class="m-field" style="width:90px;margin-left:4px" data-bind="personalisation.extra_price" value="' + (s.extra_price||0) + '"' + (s.pricing!=='extra'?' disabled':'') + '>' +
      '</label>' +
    '</div></div>' +
    '<div class="cb-field-row"><label class="cb-label">Font Style Options</label>' +
    fonts + '<button type="button" class="cb-add-btn-sm" data-action="add-font">+ Add Font</button></div>' +
    '<div class="cb-field-row"><label class="cb-label">Font Size Options <span style="color:#9CA3AF;font-weight:400">(customer picks one — leave empty to hide)</span></label>' +
    sizes + '<button type="button" class="cb-add-btn-sm" data-action="add-pers-size">+ Add Size</button></div>' +
    '<div class="cb-field-row"><label class="cb-label">Text Line Settings</label>' +
    '<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;max-width:320px;margin-top:4px">' +
      '<div><label class="cb-label-sm">Max chars per line</label><input type="number" class="m-field" data-bind="personalisation.max_chars_per_line" value="' + (s.max_chars_per_line||20) + '"></div>' +
      '<div><label class="cb-label-sm">Max lines allowed</label><input type="number" class="m-field" data-bind="personalisation.max_lines" value="' + (s.max_lines||3) + '"></div>' +
    '</div></div>' +
    '<div class="cb-info-box">ℹ️ Customers see: Yes/No toggle → Text/Logo mode → per-line inputs with font & size choices → + Add Line button.</div>';
};

// ── EVENTS ────────────────────────────────────────────────
CustomizationBuilder.prototype._on = function(el, type, fn) {
  el.addEventListener(type, fn);
  this._listeners.push({ el: el, type: type, fn: fn });
};

CustomizationBuilder.prototype._attachEvents = function() {
  var self = this;
  var c = this.container;

  // Card title
  var titleInp = c.querySelector('#cbCardTitle');
  if (titleInp) this._on(titleInp, 'input', function(e) { self.state.card_title = e.target.value; self._sync(); });

  // Show header
  var headerChk = c.querySelector('#cbShowHeader');
  if (headerChk) this._on(headerChk, 'change', function(e) { self.state.show_header = e.target.checked; self._sync(); });

  // Section toggles
  c.querySelectorAll('.cb-section-toggle').forEach(function(tog) {
    self._on(tog, 'change', function(e) {
      var key = e.target.dataset.key;
      self.state.sections[key].enabled = e.target.checked;
      var body = document.getElementById('cbBody-' + key);
      if (body) body.classList.toggle('cb-open', e.target.checked);
      var btn = c.querySelector('.cb-expand-btn[data-key="' + key + '"]');
      if (btn) btn.textContent = e.target.checked ? '▲' : '▼';
      self._sync();
    });
  });

  // Expand buttons
  c.querySelectorAll('.cb-expand-btn').forEach(function(btn) {
    self._on(btn, 'click', function() {
      var key = btn.dataset.key;
      var body = document.getElementById('cbBody-' + key);
      if (body) {
        var open = body.classList.toggle('cb-open');
        btn.textContent = open ? '▲' : '▼';
      }
    });
  });

  // data-bind inputs
  c.querySelectorAll('[data-bind]').forEach(function(inp) {
    var ev = (inp.type === 'checkbox' || inp.type === 'radio') ? 'change' : 'input';
    self._on(inp, ev, function() { self._handleBind(inp); });
    // Color preview
    if (inp.type === 'color') {
      self._on(inp, 'input', function() {
        var preview = inp.nextElementSibling;
        if (preview && preview.classList.contains('cb-color-preview')) preview.style.background = inp.value;
      });
    }
  });

  // Personalisation pricing radio
  c.querySelectorAll('input[name="persPricing"]').forEach(function(r) {
    self._on(r, 'change', function() {
      self.state.sections.personalisation.pricing = r.value;
      var extra = c.querySelector('[data-bind="personalisation.extra_price"]');
      if (extra) extra.disabled = (r.value !== 'extra');
      self._sync();
    });
  });

  // ADD/REMOVE action buttons (single delegated listener)
  var clickFn = function(e) {
    var btn = e.target.closest('[data-action]');
    if (!btn) return;
    e.preventDefault();
    self._handleAction(btn.dataset.action, btn.dataset);
  };
  self._on(c, 'click', clickFn);
};

CustomizationBuilder.prototype._handleBind = function(inp) {
  var path = inp.dataset.bind.split('.');
  var obj = this.state.sections;
  for (var i = 0; i < path.length - 1; i++) {
    var k = isNaN(path[i]) ? path[i] : parseInt(path[i]);
    obj = obj[k];
    if (!obj) return;
  }
  var last = isNaN(path[path.length-1]) ? path[path.length-1] : parseInt(path[path.length-1]);
  if (inp.type === 'checkbox') obj[last] = inp.checked;
  else if (inp.type === 'number') obj[last] = parseFloat(inp.value) || 0;
  else obj[last] = inp.value;
  this._sync();
};

CustomizationBuilder.prototype._handleAction = function(action, data) {
  var s = this.state.sections;
  switch(action) {
    case 'add-photo-slot': s.photo.slots.push({label:'',required:true}); break;
    case 'remove-photo-slot': s.photo.slots.splice(parseInt(data.idx),1); break;
    case 'add-text-field': s.text_fields.fields.push({label:'',max_chars:50,placeholder:'',required:true}); break;
    case 'remove-text-field': s.text_fields.fields.splice(parseInt(data.idx),1); break;
    case 'add-model-option': s.select_model.options.push(''); break;
    case 'remove-model-option': s.select_model.options.splice(parseInt(data.idx),1); break;
    case 'add-colour-combo': s.colour_combos.combos.push({color1:'#FF6600',color1_name:'',color2:'#000000',color2_name:'',description:''}); break;
    case 'remove-colour-combo': s.colour_combos.combos.splice(parseInt(data.idx),1); break;
    case 'add-tc-colour': {
      var si = parseInt(data.slot);
      if (!s.text_colours.slots[si]) s.text_colours.slots[si] = {title:'Text Colour '+(si+1),colours:[]};
      s.text_colours.slots[si].colours.push({name:'',hex:'#000000'});
      break;
    }
    case 'remove-tc-colour': s.text_colours.slots[parseInt(data.slot)].colours.splice(parseInt(data.idx),1); break;
    case 'add-size': s.size_options.sizes.push({label:'',extra_price:0}); break;
    case 'remove-size': s.size_options.sizes.splice(parseInt(data.idx),1); break;
    case 'add-pack': s.pack_options.packs.push({label:'',min_qty:1,price:0,discount_percent:0}); break;
    case 'remove-pack': s.pack_options.packs.splice(parseInt(data.idx),1); break;
    case 'add-font': s.personalisation.fonts.push(''); break;
    case 'remove-font': s.personalisation.fonts.splice(parseInt(data.idx),1); break;
    case 'add-pers-size': if (!s.personalisation.sizes) s.personalisation.sizes = []; s.personalisation.sizes.push({label:'',px:16}); break;
    case 'remove-pers-size': s.personalisation.sizes.splice(parseInt(data.idx),1); break;
    default: return;
  }
  this._sync();
  // Only re-render the specific section body that changed
  var sectionKey = action.split('-').slice(1).join('_');
  var bodyMap = {
    'photo_slot': 'photo', 'text_field': 'text_fields', 'model_option': 'select_model',
    'colour_combo': 'colour_combos', 'tc_colour': 'text_colours', 'size': 'size_options',
    'pack': 'pack_options', 'font': 'personalisation'
  };
  // Find the section key from the action
  var actionToSection = {
    'add-photo-slot':'photo', 'remove-photo-slot':'photo',
    'add-text-field':'text_fields', 'remove-text-field':'text_fields',
    'add-model-option':'select_model', 'remove-model-option':'select_model',
    'add-colour-combo':'colour_combos', 'remove-colour-combo':'colour_combos',
    'add-tc-colour':'text_colours', 'remove-tc-colour':'text_colours',
    'add-size':'size_options', 'remove-size':'size_options',
    'add-pack':'pack_options', 'remove-pack':'pack_options',
    'add-font':'personalisation', 'remove-font':'personalisation',
    'add-pers-size':'personalisation', 'remove-pers-size':'personalisation'
  };
  var targetKey = actionToSection[action];
  if (targetKey) {
    var bodyEl = document.getElementById('cbBody-' + targetKey);
    if (bodyEl) {
      bodyEl.innerHTML = this._renderSectionBody(targetKey);
      // Re-attach data-bind events for the updated section only
      var self = this;
      bodyEl.querySelectorAll('[data-bind]').forEach(function(inp) {
        var ev = (inp.type === 'checkbox' || inp.type === 'radio') ? 'change' : 'input';
        self._on(inp, ev, function() { self._handleBind(inp); });
        if (inp.type === 'color') {
          self._on(inp, 'input', function() {
            var prev = inp.nextElementSibling;
            if (prev && prev.classList.contains('cb-color-preview')) prev.style.background = inp.value;
          });
        }
      });
    }
  } else {
    this.render();
  }
};

// ── DRAG & DROP ───────────────────────────────────────────
CustomizationBuilder.prototype._initDrag = function() {
  var self = this;
  var list = this.container.querySelector('#cbOrderList');
  if (!list) return;
  var dragSrc = null;

  list.querySelectorAll('.cb-section-card').forEach(function(card) {
    self._on(card, 'dragstart', function(e) {
      dragSrc = card;
      e.dataTransfer.effectAllowed = 'move';
      card.classList.add('cb-dragging');
    });
    self._on(card, 'dragend', function() {
      card.classList.remove('cb-dragging');
      list.querySelectorAll('.cb-section-card').forEach(function(c) { c.classList.remove('cb-drag-over'); });
    });
    self._on(card, 'dragover', function(e) {
      e.preventDefault();
      if (card !== dragSrc) card.classList.add('cb-drag-over');
    });
    self._on(card, 'dragleave', function() { card.classList.remove('cb-drag-over'); });
    self._on(card, 'drop', function(e) {
      e.stopPropagation();
      if (!dragSrc || dragSrc === card) return;
      var cards = Array.from(list.querySelectorAll('.cb-section-card'));
      var fromIdx = cards.indexOf(dragSrc);
      var toIdx = cards.indexOf(card);
      var newOrder = self.state.section_order.slice();
      var moved = newOrder.splice(fromIdx, 1)[0];
      newOrder.splice(toIdx, 0, moved);
      self.state.section_order = newOrder;
      self._sync();
      self.render();
    });
  });
};

// ── EXPOSE ────────────────────────────────────────────────
window.CustomizationBuilder = CustomizationBuilder;

})();
