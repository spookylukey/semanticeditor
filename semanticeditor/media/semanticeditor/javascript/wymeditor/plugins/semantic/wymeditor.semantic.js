/*
 * Plugin for WYMEditor that provides an interface to allow separation
 * of presentation and content by allowing the user to select presentation
 * elements for each section.  Depends on a server-side backend to do
 * parsing and provide list of allowed CSS classes.
 */

function PresentationControls(wym, opts) {
    this.wym = wym;
    this.opts = opts;
    this.name = wym._element.get(0).name;
    // available_styles: an array of dictionaries corresponding to PresentationInfo objects
    this.available_styles = new Array();
    // presentation_info: a dictionary of { sect_id : [PresentationInfo] }
    this.presentation_info = {};

    // commands: an array of dictionaries corresponding to PresentationInfo objects for commands.
    this.commands = new Array();
    // command_dict: a dictionary mapping command name to PresentationInfo object.
    this.command_dict = {};

    // the node of the current block level element being edited.
    this.current_node = null;

    // Need to sync with presentation.py
    this.blockdef_selector = "h1,h2,h3,h4,h5,h6,p,ol,ul,blockquote,li,pre";

    this.setup_controls(jQuery(wym._bvox).find(".wym_area_bottom"));
}

function escapeHtml(html) {
    return html.replace(/&/g,"&amp;")
        .replace(/\"/g,"&quot;")
        .replace(/</g,"&lt;")
        .replace(/>/g,"&gt;");
}

function flattenPresStyle(pres) {
    // Convert a PresentationInfo object to a string
    return pres.prestype + ":" + pres.name;
}

function expandPresStyle(presstr) {
    // Convert a string to PresentationInfo object
    var comps = presstr.match(/^([^:]+):(.*)$/);
    return { prestype: comps[1],
             name: comps[2] };
}


PresentationControls.prototype.setup_css_storage = function() {
    // We need a place to store custom CSS rules. (Existing jQuery plugins don't
    // allow for our need of changing style sheet of document in an iframe, and
    // rolling our own is easier than fixing them).

    // code partly copied from jquery.cssRule.js
    var cssStorageNode = jQuery('<style rel="stylesheet" type="text/css">').appendTo(jQuery(this.wym._doc).find("head"))[0];
    this.stylesheet = this.wym._doc.styleSheets[0];
};

PresentationControls.prototype.add_css_rule = function(selector, rule) {
    var ss = this.stylesheet;
    var rules = ss.rules ? 'rules' : 'cssRules';
    // should work with IE and Firefox, don't know about Safari
    if (ss.addRule)
        ss.addRule(selector, rule||'x:y' );//IE won't allow empty rules
    else if (ss.insertRule)
        ss.insertRule(selector + '{'+ rule +'}', ss[rules].length);
};

PresentationControls.prototype.setup_controls = function(container) {
    var id_prefix = "id_prescontrol_" + this.name + "_";
    var previewbutton_id = id_prefix + 'previewbutton';
    var previewbox_id = id_prefix + 'previewbox';
    var cleanhtmlbutton_id = id_prefix + 'cleanhtmlbutton';
    var self = this;

    // Create elements
    container.after(
        "<div class=\"prescontrol\">" +
            "<input type=\"submit\" value=\"Clean pasted HTML\" id=\"" + cleanhtmlbutton_id  +  "\" />" +
            "<input type=\"submit\" value=\"Preview\" id=\"" + previewbutton_id + "\" />" +
            "<div class=\"prescontrolerror\" id=\"" + id_prefix + "errorbox" + "\"></div>" +
        "</div>");

    jQuery("body").append("<div style=\"position: absolute; display: none\" class=\"previewbox\" id=\"" + previewbox_id + "\">");

    this.classlist = jQuery(this.wym._options.classesSelector).find("ul");
    this.commandlist = jQuery(this.wym._options.layoutCommandsSelector).find("ul");
    this.errorbox = jQuery('#' + id_prefix + "errorbox");
    this.previewbutton = jQuery('#' + previewbutton_id);
    this.previewbox = jQuery('#' + previewbox_id);
    this.cleanhtmlbutton = jQuery('#' + cleanhtmlbutton_id);

    this.setup_css_storage();

     // Initial set up
    // Remove any tooltips
    jQuery(".orbitaltooltip-simplebox").unbind().remove();

    this.retrieve_commands(); // async
    this.retrieve_styles(); // async
    this.separate_presentation();

    this.previewbutton.toggle(function(event) {
                                 self.show_preview();
                                 return false;
                              },
                              function(event) {
                                  self.previewbox.hide();
                              });
    this.cleanhtmlbutton.click(function(event) {
                                   self.clean_html();
                                   return false;
                               });
    jQuery(this.wym._doc)
        .bind("keyup", function(evt) {
                  // this style of binding give doc_keyup
                  // access to 'this' PresentationControl
                  self.doc_keyup(evt);
              })
        .bind("mouseup", function(evt) {
                  self.doc_mouseup(evt);
              });

    // Insert rewriting of HTML before the WYMeditor updates the textarea.
    jQuery(this.wym._options.updateSelector)
        .bind(this.wym._options.updateEvent, function(event) {
                  self.form_submit(event);
              });

    // Fix height of classlist (in timeout to give command list time to load)
    setTimeout(function() {
                   var h = jQuery(" .wym_area_main").height() -
                       jQuery(self.wym._options.containersSelector).height() -
                       jQuery(self.wym._options.layoutCommandsSelector).height() -
                       jQuery(self.wym._options.classesSelector + " h2").height() -
                       20; // 20 is a fudge value, probably equal to some marings/paddings
                   self.classlist.css("height", h.toString() + "px");
               }, 1000);

    // Stop the tooltips from getting in the way - dismiss with a click.
    // (in timeout to give them time to be created)
    setTimeout(function() {
                   jQuery(".orbitaltooltip-simplebox").click(function(event) {
                                                                 jQuery(this).hide();
                                                             });
               }, 1000);

};

PresentationControls.prototype.set_html = function(html) {
    // WUMEditor ought to call .listen() after setting
    // the HTML (to rebind events for images),
    // but it doesn't at the moment, so we work around it by wrapping.
    this.wym.html(html);
    this.wym.listen();
};

PresentationControls.prototype.doc_keyup = function(evt) {
    // Some browsers (Firefox at least) will insert a new paragraph with the
    // same ID as the old one when the user presses 'Enter'. This needs fixing
    // for our styling to work. It's possible that multiple 'p' elements can be inserted
    // for one keyup event, so we handle that. This appears to happen for any
    // elements that are created by pressing 'Enter'

    // We also need to update the disable/enabled state of the classlist and commandlist
    var self = this;
    var wym = self.wym;
    var container = jQuery(wym.selected()).parentsOrSelf(this.blockdef_selector);
    if (evt.keyCode == 13 && !evt.shiftKey) {
        if (container.is("p[id],li[id]")) {
            // Need to clear id on all elem's with that id except the first.
            // (hoping that jQuery will return them in document order, which it
            // seems to)
            jQuery(wym._doc).find(container.get(0).tagName + "#" +  container.attr("id")).
                each(function(i){
                         var node = this;
                         if (i > 0) { // skip the first
                              jQuery(node).removeAttr('id');
                         }
                     });
        }
    }
    this.update_classlist_item_all(container);
};

PresentationControls.prototype.doc_mouseup = function(evt) {
    this.update_classlist_item_all();
};

PresentationControls.prototype.update_classlist_item_all = function(cur_container) {
    var self = this;
    if (cur_container == undefined) {
        cur_container = jQuery(this.wym.selected()).parentsOrSelf(this.blockdef_selector);
    }
    var node = cur_container.get(0);
    if (node != undefined && node != this.current_node) {
        // if current node has changed, might need to update list
        this.current_node = node;
        // Sets enabled/disabled on all items in classlist and commands
        var pairs = [[this.available_styles, this.classlist],
                     [this.commands, this.commandlist]];

        for (var i = 0; i < pairs.length; i++) {
            var styles = pairs[i][0];
            var btncontainer = pairs[i][1];
            btncontainer.find("a").each(function(k) {
                                            self.update_classlist_item(jQuery(this), styles[k]);
                                        });
        }
    }


};

// Splits the HTML into 'content HTML' and 'presentation'
PresentationControls.prototype.separate_presentation = function() {
    // 'andthen' is a function to do afterwards.  This is a nasty
    // hack to get things to work.
    var self = this;
    jQuery.post(this.opts.separate_presentation_url, { html: self.wym.xhtml() } ,
                function(data) {
                    self.with_good_data(data,
                        function(value) {
                            // Store the presentation
                            self.presentation_info = value.presentation;
                            // Update the HTML
                            self.set_html(value.html);
                            // Update presentation of HTML
                            self.update_after_loading();
                        });
                }, "json");
};

PresentationControls.prototype.ensure_all_ids = function() {
    // We check all block level elements (or all elements that can have commands
    // applied to them)

    var self = this;
    var elems = [];
    for (var i = 0; i < this.commands.length; i++) {
        elems = jQuery.merge(elems, this.commands[i].allowed_elements);
    }
    elems = jQuery.unique(elems);
    jQuery(this.wym._doc).find(elems.join(",")).each(function(i) {
                                                         self.ensure_id(this);
                                                     });
};

PresentationControls.prototype.clean_presentation_info = function() {
    // clear out orphaned items
    var orphaned = [];
    for (var key in this.presentation_info) {
        var sel = "#" + key;
        if (!jQuery(this.wym._doc).find(sel).is(sel)) {
            orphaned.push(key);
        }
    }
    for (var i = 0; i < orphaned.length; i++) {
        delete this.presentation_info[orphaned[i]];
    }
};

PresentationControls.prototype.form_submit = function(event) {
    // We need to ensure all elements have ids, *and* that command block
    // elements have correct ids (which is a side effect of the below).
    this.ensure_all_ids();
    // this.presentation_info might have old info, if command blocks have
    // been removed.  Need to clean.
    this.clean_presentation_info();

    // Since we are in the middle of submitting the page, an asynchronous
    // request will be too late! So we block instead.

    // TODO - exception handling.  If this fails, the default
    // handler will post the form, causing all formatting to be lost.
    var res = jQuery.ajax({
                  type: "POST",
                  data: {
                      html: this.wym.xhtml(),
                      presentation: JSON.stringify(this.presentation_info)
                  },
                  url: this.opts.combine_presentation_url,
                  dataType: "json",
                  async: false
    }).responseText;
    var data = JSON.parse(res);
    if (data.result == 'ok') {
        // Replace existing HTML with combined.
        this.set_html(data.value.html);
        // In case the normal WYMeditor update got called *before* this
        // event handler, we do another update.
        this.wym.update();
    } else {
        event.preventDefault();
        this.show_error(data.message);
        alert("Data in " + this.name + " can't be saved - see error message.");
    }
};

PresentationControls.prototype.build_classlist = function() {
    this.classlist.empty();

    var self = this;
    jQuery.each(this.available_styles, function(i, item) {
        var btn = jQuery("<li><a href='#'>" + escapeHtml(item.verbose_name) + "</a></li>").appendTo(self.classlist).find("a");
        // event handlers
        var style = self.available_styles[i];
        btn.click(function(event) {
                      self.toggle_style(style);
                  });

        // Attach tooltip to button we just added:
        var help = item.description;
        if (help == "") {
            help = "(No help available)";
        }
        help = "<h1>" + escapeHtml(item.verbose_name) + "</h1>" + help;
        help = help + '<br/><hr/><p>Can be used on these elements:</p><p>' + item.allowed_elements.join(' ') + '</p>';
        // Assign an id, because orbitaltooltip doesn't work without it.
        btn.attr('id', 'id_classlist_' + i);
        setTimeout(function() {
                       btn.orbitaltooltip({
                           orbitalPosition: 270,
                           // Small spacing means we can move onto the tooltip
                           // in order to scroll it if the help text has
                           // produced scroll bars.
                           spacing:         8,
                           tooltipClass:         'orbitaltooltip-simplebox',
                           html:            help
                       });
        }, 1000); // Delay, otherwise tooltips can end up in wrong position.
    });


};

PresentationControls.prototype.build_commandlist = function() {
    this.commandlist.empty();

    var self = this;
    jQuery.each(this.commands, function(i, item) {
        var btn = jQuery("<li><a href='#'>" + escapeHtml(item.verbose_name) + "</a></li>").appendTo(self.commandlist).find("a");
        // event handlers
        var command = self.commands[i];

        btn.click(function(event) {
                      self.do_command(command);
                  });
        btn.hover(function(event) {
                      // update_classlist_item works for
                      // commands as well as classes.
                     self.update_classlist_item(btn, command);
                  });

        // Attach tooltip to label we just added:
        var help = item.description;
        if (help == "") {
            help = "(No help available)";
        }
        help = "<h1>" + escapeHtml(item.verbose_name) + "</h1>" + help;
        help = help + '<br/><hr/><p>Can be inserted on these elements:</p><p>' + item.allowed_elements.join(' ') + '</p>';
        // Assign an id, because orbitaltooltip doesn't work without it.
        btn.attr('id', 'id_commandlist_' + i);
        setTimeout(function() {
                       btn.orbitaltooltip({
                           orbitalPosition: 270,
                           // Small spacing means we can move onto the tooltip
                           // in order to scroll it if the help text has
                           // produced scroll bars.
                           spacing:         8,
                           tooltipClass:         'orbitaltooltip-simplebox',
                           html:            help
                       });
        }, 1000); // Delay, otherwise tooltips can end up in wrong position.
    });

};

PresentationControls.prototype.has_style = function(sect_id, style) {
    var styles = this.presentation_info[sect_id];
    for (var i = 0; i < styles.length; i++) {
        if (flattenPresStyle(styles[i]) == flattenPresStyle(style)) {
            return true;
        };
    }
    return false;
};

PresentationControls.prototype.next_id = function(tagName) {
    // All sections that can receive styles need a section ID.
    // For the initial HTML, this is assigned server-side when the
    // HTML is split into 'semantic HTML' and 'presentation info'.
    // For newly added HTML, however, we need to add it ourself

    var i = 1;
    var id = "";
    while (true) {
        id = tagName + "_" + i.toString();
        if (jQuery(this.wym._doc).find('#' + id).is(tagName)) {
            i++;
        } else {
            return id;
        }
    }
};

PresentationControls.prototype.update_command_blocks = function(node, id, max) {
    if (max == 0) {
        return;
    };
    var prev = node.previousSibling;
    if (prev != undefined && prev.tagName != undefined && prev.tagName.toLowerCase() == 'p') {
        // command blocks are like <p id="newrow_p_1" class="newrow">
        // check we've got a command block.
        var className = prev.className;
        var prev_id = prev.id;
        if (prev_id && prev_id.match(eval("/^" + className + "/"))) {
            prev.id = className + "_" + id;
            // need to update presentation_info as well
            this.presentation_info[prev.id] = this.presentation_info[prev_id];
            delete this.presentation_info[prev_id];
            // and then the visible indicators
            this.update_style_display(prev.id);
            // do the next one.
            this.update_command_blocks(prev, id, max - 1);
        }
    }
};

PresentationControls.prototype.assign_id = function(node, id) {
    // Assign an ID to an element.  This can be tricky, because, if the section
    // has a command block before it, we need to make sure that the id of those
    // blocks are changed, since the 'position' of the command blocks are only stored
    // by giving them the right id.
    node.id = id;
    // Need to change (up to) the two previous siblings.
    this.update_command_blocks(node, id, 2);
};

PresentationControls.prototype.register_section = function(sect_id) {
    // Make sure we have somewhere to store styles for a section.
    this.presentation_info[sect_id] = new Array();
};

PresentationControls.prototype.tagname_to_selector = function(name) {
    // Convert a tag name into a selector used to match elements that represent
    // that tag.  This function accounts for the use of p elements to represent
    // commands in the document

    var c = this.command_dict[name];
    if (c == null) {
        // not a command
        if (name == "p") {
            // Need to ensure we don't match commands
            var selector = "p";
            for (var i = 0; i < this.commands.length; i++) {
                selector = selector + "[class!='" + this.commands[i].name + "']";
            }
            return selector;
        } else {
        return name;
        }
    } else {
        return "p." + c.name;
    }
};

PresentationControls.prototype.ensure_id = function(node) {
    var id = node.id;

    if (id == undefined || id == "") {
        id = this.next_id(node.tagName.toLowerCase());
        this.assign_id(node, id);
        this.register_section(id);
    }
    return id;
};

PresentationControls.prototype.get_current_section = function(style) {
    // Returns the section ID of the current section that is applicable
    // to the given style, or undefined if there is none.
    // Since sections can be nested, if more than one section is possible
    // for the given style, the first section found (starting from the
    // current selection and moving up the HTML tree) will be returned.
    // This function has the side effect of adding a section ID if one
    // was not defined already.
    var wym = this.wym;
    var self = this;
    var expr = jQuery.map(style.allowed_elements,
                          function(t,i) { return self.tagname_to_selector(t); }
                         ).join(",");
    var container = jQuery(wym.selected()).parentsOrSelf(expr);
    if (container.is(expr)) {
        var first = container.get(0);
        var id = this.ensure_id(first);
        return id;
    }
    return undefined;
};

PresentationControls.prototype.toggle_style = function(style) {
    // What section are we on?
    var sect_id = this.get_current_section(style);
    if (sect_id == undefined) {
        // No allowed to use it there
        alert("Cannot use this style on current element.");
        return;
    }

    if (this.has_style(sect_id, style)) {
        this.remove_style(sect_id, style);
    } else {
        this.add_style(sect_id, style);
    }
    this.update_style_display(sect_id);
};

PresentationControls.prototype.insert_command_block = function(sect_id, command) {
    // There is some custom logic about the different commands here i.e.
    // that newrow should appear before newcol.
    var newelem = jQuery("<p class=\"" + command.name + "\">*</p>");
    var elem = jQuery(this.wym._doc).find("#" + sect_id);
    // New row should appear before new col
    if (elem.prev().is("p.newcol") && command.name == 'newrow') {
        elem = elem.prev();
    }
    elem.before(newelem);
    var new_id = command.name + "_" + sect_id; // duplication with do_command
    newelem.attr('id', new_id);
    this.update_style_display(new_id);
    return new_id;
};

PresentationControls.prototype.do_command = function(command) {
    // What section are we on?
    var sect_id = this.get_current_section(command);
    if (sect_id == undefined) {
        // No allowed to use it there
        alert("Cannot use this command on current element.");
        return;
    }
    var new_id = command.name + "_" + sect_id; // duplication with insert_command_block
    this.register_section(new_id);
    this.presentation_info[new_id].push(command);
    // newrow and newcol are the only commands at the moment.
    // We handle both using inserted blocks
    this.insert_command_block(sect_id, command);
};

PresentationControls.prototype.insert_command_blocks = function() {
    // This is run once, after loading HTML.  We can rely on 'ids' being
    // present, since the HTML is all sent by the server.
    for (var key in this.presentation_info) {
        var presinfos = this.presentation_info[key];
        for (var i = 0; i < presinfos.length; i++) {
            var pi = presinfos[i];
            if (pi.prestype == 'command') {
                var id = key.split('_').slice(1).join('_');
                this.insert_command_block(id, this.command_dict[pi.name]);
            }
        }
    }
};

PresentationControls.prototype.update_classlist_item = function(btn, style) {
    var self = this;
    var sect_id = this.get_current_section(style);
    if (sect_id == undefined) {
        // Can't use it.
        if (style.prestype == "command")
            // Don't want the class list (displayed below command list)
            // to jump up and down
            btn.addClass("disabled");
        else
            btn.hide();
    } else {
        if (style.prestype == "command")
            btn.removeClass("disabled");
        else
            btn.show();
    }
};

PresentationControls.prototype.show_preview = function() {
    var self = this;
    this.ensure_all_ids();
    this.clean_presentation_info();
    jQuery.post(this.opts.preview_url, { 'html': self.wym.xhtml(),
                                         'presentation': JSON.stringify(this.presentation_info)
                                        },
                function(data) {
                    self.with_good_data(data,
                        function(value) {
                            var btn = self.previewbutton;
                            var box = self.previewbox;
                            var pos = btn.offset();
                            box.html(value.html);
                            var height = box.height() + parseInt(box.css('padding-top')) + parseInt(box.css('padding-bottom')) +
                                parseInt(box.css('border-top-width')) + parseInt(box.css('border-bottom-width'));
                            box.css("top", pos.top - height).css("left", pos.left);
                            box.show();
                        });
                }, "json");
    return false;
};

PresentationControls.prototype.add_style = function(sect_id, presinfo) {
    var styles = this.presentation_info[sect_id];
    styles.push(presinfo);
    this.presentation_info[sect_id] = jQuery.unique(styles);
};

PresentationControls.prototype.remove_style = function(sect_id, presinfo) {
    var styles = this.presentation_info[sect_id];
    styles = jQuery.grep(styles, function(item, i) {
                             return !(item.prestype == presinfo.prestype
                                      && item.name == presinfo.name);
                         });
    this.presentation_info[sect_id] = styles;
};

PresentationControls.prototype.update_style_display = function(sect_id) {
    var styles = this.presentation_info[sect_id];
    var self = this;
    var style_list = jQuery.map(styles, function(s, i) {
                                    return self.get_verbose_style_name(s.name);
                                }).join(", ");
    this.add_css_rule("#" + sect_id + ":before", 'content: "' + style_list + '"');
};

PresentationControls.prototype.update_all_style_display = function() {
    for (var key in this.presentation_info) {
        this.update_style_display(key);
    }
};

PresentationControls.prototype.update_after_loading = function() {
    this.insert_command_blocks();
    this.update_all_style_display();
};

PresentationControls.prototype.get_verbose_style_name = function(stylename) {
    // Full style information is not stored against individual headings, only
    // the type and name. So sometimes we need to go from one to the other.

    var styles = this.available_styles;
    for (var i = 0; i < styles.length; i++) {
        if (styles[i].name == stylename) {
            return styles[i].verbose_name;
        }
    }
    var commands = this.commands;
    for (var i2 = 0; i2 < commands; i2++) {
        if (commands[i2].name == stylename) {
            return commands[i2].verbose_name;
        }
    }
    return undefined; // shouldn't get here
};

PresentationControls.prototype.clean_html = function() {
    var self = this;
    var html = this.wym.xhtml();
    jQuery.post(this.opts.clean_html_url, {'html':html},
                function(data) {
                    self.with_good_data(data, function(value) {
                                            self.set_html(value.html);
                                            self.update_after_loading();
                                        });
                }, "json");
};

// If data contains an error message, display to the user,
// otherwise clear the displayed error and perform the callback
// with the value in the data.
PresentationControls.prototype.with_good_data = function(data, callback) {
    if (data.result == 'ok') {
        this.clear_error();
        callback(data.value);
    } else {
        // TODO - perhaps distinguish between a server error
        // and a user error
        this.show_error(data.message);
    }
};

PresentationControls.prototype.clear_error = function() {
    this.errorbox.empty();
};

PresentationControls.prototype.show_error = function(message) {
    this.clear_error();
    this.errorbox.append(escapeHtml(message));
};

PresentationControls.prototype.retrieve_styles = function() {
    var self = this;
    // Needs async=false, since separate_presentation depends on data.
    var res = jQuery.ajax({
                  type: "GET",
                  data: {
                      'template':this.opts.template,
                      'page_id':this.opts.page_id
                  },
                  url: this.opts.retrieve_styles_url,
                  dataType: "json",
                  async: false
    }).responseText;
    var data = JSON.parse(res);

    self.with_good_data(data, function(value) {
        self.available_styles = data.value;
        self.build_classlist();
    });
};

PresentationControls.prototype.retrieve_commands = function() {
    var self = this;
    // Needs async=false, since separate_presentation depends on data.
    var res = jQuery.ajax({
                  type: "GET",
                  data: {},
                  url: this.opts.retrieve_commands_url,
                  dataType: "json",
                  async: false
    }).responseText;
    var data = JSON.parse(res);

    self.with_good_data(data, function(value) {
                            self.commands = data.value;
                            for (var i = 0; i < self.commands.length; i++) {
                                var c = self.commands[i];
                                self.command_dict[c.name] = c;
                            }
                            self.build_commandlist();
                        });
};

// The actual WYMeditor plugin:
WYMeditor.editor.prototype.semantic = function(options) {
    var wym = this;
    var c = new PresentationControls(wym, options);
};
