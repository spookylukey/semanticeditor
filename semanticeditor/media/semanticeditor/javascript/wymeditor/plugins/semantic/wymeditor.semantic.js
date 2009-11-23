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
    // stored_headings: array of StructureItem objects (attributes .level, .name, .sect_id, .tag)
    this.stored_headings = new Array();
    // active_heading_list - a possibly filtered version of stored_headings
    this.active_heading_list = new Array();
    // presentation_info: a dictionary of { sect_id : [PresentationInfo] }
    this.presentation_info = {};

    this.setup_controls(jQuery(wym._box).find(".wym_area_bottom"));
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
    var headingsbox_id = id_prefix + 'headings';
    var headingsfilter_id = id_prefix + 'headingsfilter';
    var previewbutton_id = id_prefix + 'previewbutton';
    var previewbox_id = id_prefix + 'previewbox';
    var refresh_id = id_prefix + 'refresh';
    var newrowbutton_id = id_prefix + 'newrowbutton';
    var newcolbutton_id = id_prefix + 'newcolbutton';
    var removebutton_id = id_prefix + 'removebutton';
    var cleanhtmlbutton_id = id_prefix + 'cleanhtmlbutton';
    var self = this;

    // Create elements
    container.after(
        "<div class=\"prescontrol\">" +
        "<input type=\"submit\" value=\"New row\" id=\"" + newrowbutton_id  +"\" />" +
        "<input type=\"submit\" value=\"New column\" id=\"" + newcolbutton_id  +"\" />" +
        "<input type=\"submit\" value=\"Remove\" id=\"" + removebutton_id  +"\" />" +
        "</div>" +
        "<div class=\"prescontrolheadings\" style=\"margin-right: 260px;\">Document structure:<br/><select size=\"15\" id=\"" + headingsbox_id + "\"></select>" +
        "<br/><label><input type=\"checkbox\" id=\"" + headingsfilter_id + "\"> Headings only</label></div>" +

        "<table width=\"100%\" border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr>" +
            "<td><input type=\"submit\" value=\"Clean pasted HTML\" id=\"" + cleanhtmlbutton_id  +  "\" /></td>" +
            "<td><input type=\"submit\" value=\"Refresh structure\" id=\"" + refresh_id + "\" /></td>" +
            "<td><input type=\"submit\" value=\"Preview\" id=\"" + previewbutton_id + "\" /></td>" +
            "<td width=\"100%\"><div class=\"prescontrolerror\" id=\"" + id_prefix + "errorbox" + "\"></div></td></tr></table>" +
        "</div>");

    jQuery("body").append("<div style=\"position: absolute; display: none\" class=\"previewbox\" id=\"" + previewbox_id + "\">");

    this.classlist = jQuery(this.wym._options.classesSelector).find("ul");
    this.headingscontrol = jQuery('#' + headingsbox_id);
    this.headingsfilter = jQuery('#' + headingsfilter_id);
    this.errorbox = jQuery('#' + id_prefix + "errorbox");
    this.previewbutton = jQuery('#' + previewbutton_id);
    this.previewbox = jQuery('#' + previewbox_id);
    this.refreshbutton = jQuery('#' + refresh_id);
    this.newrowbutton = jQuery('#' + newrowbutton_id);
    this.newcolbutton = jQuery('#' + newcolbutton_id);
    this.removebutton = jQuery('#' + removebutton_id);
    this.cleanhtmlbutton = jQuery('#' + cleanhtmlbutton_id);
    // TODO - height of classlist box?

    this.setup_css_storage();

     // Initial set up
    this.retrieve_styles();
    // refresh_headings must come after separate_presentation
    this.separate_presentation(function() { self.refresh_headings(); });

    // Event handlers
    this.headingscontrol.change(function(event) {

    });
    this.refreshbutton.click(function(event) {
                                 self.refresh_headings();
                                 self.headingscontrol.get(0).focus();
                                 return false;
                             });
    this.previewbutton.toggle(function(event) {
                                 self.show_preview();
                                 return false;
                              },
                              function(event) {
                                  self.previewbox.hide();
                              });
    this.headingsfilter.change(function(event) {
                                   self.update_active_heading_list();
                                   self.update_headingbox();
                               });
    this.newrowbutton.click(function(event) {
                                self.insert_row();
                                return false;
                            });
    this.newcolbutton.click(function(event) {
                                self.insert_column();
                                return false;
                            });
    this.removebutton.click(function(event) {
                                self.remove_layout_command();
                                return false;
                            });
    this.cleanhtmlbutton.click(function(event) {
                                   self.clean_html();
                                   return false;
                               });
    // Insert rewriting of HTML before the WYMeditor updates the textarea.
    jQuery(this.wym._options.updateSelector)
        .bind(this.wym._options.updateEvent, function(event) {
                  self.form_submit(event);
              });

};

PresentationControls.prototype.set_html = function(html) {
    // WUMEditor ought to call .listen() after setting
    // the HTML (to rebind events for images),
    // but it doesn't at the moment, so we work around it by wrapping.
    this.wym.html(html);
    this.wym.listen();
};

// Splits the HTML into 'content HTML' and 'presentation'
PresentationControls.prototype.separate_presentation = function(andthen) {
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
                            if (andthen != null) {
                                andthen();
                            }
                        });
                }, "json");
};

PresentationControls.prototype.form_submit = function(event) {
    // Since we are in the middle of submitting the page, an asynchronous
    // request will be too late! So we block instead.
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
    // Remove any tooltips
    jQuery(".orbitaltooltip-simplebox").unbind().remove();

    var self = this;
    jQuery.each(this.available_styles, function(i, item) {
        var btn = jQuery("<li><a href='#'>" + escapeHtml(item.verbose_name) + "</a></li>").appendTo(self.classlist).find("a");
        // event handlers
        var style = self.available_styles[i];
        btn.click(function(event) {
                      self.toggle_style(style);
                  });
        btn.hover(function(event) {
                     self.update_classlist_item(btn, style);
                  });

        // Attach tooltip to label we just added:
        var help = item.description;
        if (help == "") {
            help = "(No help available)";
        }
        help = "<h1>" + escapeHtml(item.verbose_name) + "</h1>" + help;
        help = help + '<br/><hr/><p>Can be used on these elements:</p><p>' + item.allowed_elements.join(' ') + '</p>';
        // Assign an id, because orbitaltooltip
        // doesn't work without it.
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
    // Stop the tooltips from getting in the way
    // - dismiss with a click.
    jQuery(".orbitaltooltip-simplebox").click(function(event) {
                                                  jQuery(this).hide();
                                              });
};

PresentationControls.prototype.unbind_classlist = function() {
    // Remove existing event handlers, reset state
    this.classlist.find("a").unbind().addClass("disabled");
};

PresentationControls.prototype.get_heading_index = function() {
    var selected = this.headingscontrol.get(0).value;
    if (!selected) {
        return null;
    }
    return parseInt(selected, 10);
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

PresentationControls.prototype.assign_id = function(node) {
    // All sections that can receive styles need a section ID.
    // For the initial HTML, this is assigned server-side when the
    // HTML is split into 'semantic HTML' and 'presentation info'.
    // For newly added HTML, however, we need to add it ourself

    var tagName = node.tagName.toLowerCase();
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

PresentationControls.prototype.register_section = function(sect_id, tag) {
    // This is a temporary fix to make sure variables are in consistent
    // state. We have to do a server side call to get proper values,
    // but we delay that until needed.

    var structureItem = {
        sect_id: sect_id,
        tag: tag,
        level: undefined, // Difficult to calculate client side
        name: undefined // Difficult to calculate client side
    };
    this.stored_headings.push(structureItem);
    this.presentation_info[sect_id] = Array();
};

PresentationControls.prototype.get_current_section = function(style) {
    var wym = this.wym;
    // TODO - images for new row/column
    // var container = (wym._selected_image ? wym._selected_image 
    //                 : jQuery(wym.selected()));
    // TODO - limit selection to allowed elements for style - fix for 'row', 'col'

    var expr = style.allowed_elements.join(",");
    var container = jQuery(wym.selected()).parentsOrSelf(expr);
    if (container.is(expr)) {
        var first = container.get(0);
        var id = first.id;
        if (id == undefined || id == "") {
            id = this.assign_id(first);
            this.register_section(id, first.tagName.toLowerCase());
            first.id = id;
        }
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
    }

    if (this.has_style(sect_id, style)) {
        this.remove_style(sect_id, style);
    } else {
        this.add_style(sect_id, style);
    }
    this.update_style_display(sect_id);
};

PresentationControls.prototype.update_classlist_item = function(btn, style) {
    var self = this;
    var sect_id = this.get_current_section(style);
    if (sect_id == undefined) {
        // Can't use it.
        btn.addClass("disabled");
    } else {
        btn.removeClass("disabled");
    }
};

PresentationControls.prototype.show_preview = function() {
    var self = this;
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
    if (sect_id.match(/^nerow_/)) {
        // TODO
    } else if (sect_id.match(/^newcol_/)) {
        // TODO
    } else {
        this.add_css_rule("#" + sect_id + ":before", 'content: "' + style_list + '"');
    }
};

PresentationControls.prototype.update_all_style_display = function() {
    for (var i=0; i < this.stored_headings.length; i++) {
        this.update_style_display(this.stored_headings[i].sect_id);
    }
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
    if (stylename == "newrow") {
        return "New row";
    } else if (stylename == "new column") {
        return "New column";
    }
    return undefined; // shouldn't get here
};

PresentationControls.prototype.insert_row = function() {
    // Insert a new row command into outline above selected item
    var headingIndex = this.get_heading_index();
    if (headingIndex == null) return;
    var sect_id = this.active_heading_list[headingIndex].sect_id;
    if (sect_id.match(/^newrow_/)) {
        alert("Can't insert new row here");
        return;
    }

    for (var i=0; i < this.stored_headings.length; i++) {
        if (this.stored_headings[i].sect_id == sect_id) {
            // Update the headings:
            this.insert_row_command(this.stored_headings, i, sect_id);
            // Update presentation info:
            // An empty array will do, don't actually need a
            // command in there (and the GUI will overwrite any
            // anything we put in it)
            this.presentation_info['newrow_' + sect_id] = Array();
            break;
        }
    }

    // Refresh GUI
    this.update_active_heading_list();
    this.update_headingbox();

    // select what was selected before
    this.headingscontrol.get(0).value = headingIndex;
};

PresentationControls.prototype.insert_row_command = function(arr, i, sect_id) {
    arr.splice(i, 0, {level:1,
                      name:"New row",
                      tag:"row",
                      sect_id:"newrow_" + sect_id
                     });
};


PresentationControls.prototype.insert_column = function() {
    // Insert a new row command into outline above selected item
    var headingIndex = this.get_heading_index();
    if (headingIndex == null) return;
    var sect_id = this.active_heading_list[headingIndex].sect_id;
    if (sect_id.match(/^newrow_/) || sect_id.match(/^newcol_/)) {
        alert("Can't insert new column here");
        return;
    }

    for (var i=0; i < this.stored_headings.length; i++) {
        if (this.stored_headings[i].sect_id == sect_id) {
            // Update the headings:
            this.insert_column_command(this.stored_headings, i, sect_id);
            // Update presentation info:
            // An empty array will do, don't actually need a
            // command in there (and the GUI will overwrite any
            // anything we put in it)
            this.presentation_info['newcol_' + sect_id] = Array();
            break;
        }
    }
    // Refresh GUI
    this.update_active_heading_list();
    this.update_headingbox();

    // select what was selected before
    this.headingscontrol.get(0).value = headingIndex;
};

PresentationControls.prototype.insert_column_command = function(arr, i, sect_id) {
    arr.splice(i, 0, {level:1,
                      name:"New column",
                      tag:"column",
                      sect_id:"newcol_" + sect_id
                     });
};

PresentationControls.prototype.remove_layout_command = function() {
    var headingIndex = this.get_heading_index();
    if (headingIndex == null) return;
    var sect_id = this.active_heading_list[headingIndex].sect_id;
    if (!sect_id.match(/^newrow_/) && !sect_id.match(/^newcol_/)) {
        alert("Can only use 'remove' on new row or column commands");
        return;
    }
    // Update heading list
    this.stored_headings.splice(headingIndex, 1);
    // Update presentation info
    delete this.presentation_info[sect_id];
    // Refresh GUI
    this.update_active_heading_list();
    this.update_headingbox();

    if (headingIndex > 0) {
        this.headingscontrol.get(0).value = headingIndex - 1;
    }
};

PresentationControls.prototype.clean_html = function() {
    var self = this;
    var html = this.wym.xhtml();
    jQuery.post(this.opts.clean_html_url, {'html':html},
                function(data) {
                    self.with_good_data(data, function(value) {
                                            self.set_html(value.html);
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

PresentationControls.prototype.refresh_headings = function() {
    var self = this;
    var html = this.wym.xhtml();
    jQuery.post(this.opts.extract_structure_url, { 'html':html },
        function(data) {
            self.with_good_data(data, function(value) {
                self.stored_headings = value;
                self.add_layout_to_headings();
                self.update_active_heading_list();
                self.update_headingbox();
                self.update_all_style_display();
            });
        }, "json");
};

PresentationControls.prototype.add_layout_to_headings = function() {
    // Row/Column info is transmitted as part of presentation info
    // but it is displayed in the headings list, because it represents
    // divs that are inserted (and can be styled).  So we need to
    // update this.stored_headings using this.presentation_info
    var first_sect_id;
    if (this.stored_headings.length > 0) {
        first_sect_id = this.stored_headings[0].sect_id;
    } else {
        first_sect_id = '';
    }
    for (var i = 0; i < this.stored_headings.length; i++) {
        // Loop through, if any have corresponding newrow or newcol
        // entries, then add them into list.
        var sect_id = this.stored_headings[i].sect_id;
        if (this.presentation_info['newrow_' + sect_id] != null) {
            this.insert_row_command(this.stored_headings, i, sect_id);
            i++;
        }
        if (this.presentation_info['newcol_' + sect_id] != null) {
            this.insert_column_command(this.stored_headings, i, sect_id);
            i++;
        }
    }

    if (this.stored_headings.length > 0) {
        // If after this process we don't have newrow and newcol commands
        // at the beginning of the heading list, we add them.
        if (this.stored_headings[0].tag != 'row') {
            this.insert_row_command(this.stored_headings, 0, first_sect_id);
        }
        if (this.stored_headings[1].tag != 'column') {
            this.insert_column_command(this.stored_headings, 1, first_sect_id);
        }
    }

};


PresentationControls.prototype.update_active_heading_list = function() {
    var self = this;
    var items;
    if (this.headingsfilter.get(0).checked) {
        items = jQuery.grep(self.stored_headings,
                            function(item, idx) {
                                return (item.tag.toUpperCase()).match(/H\d/);
                            });
    } else {
        items = self.stored_headings;
    }
    self.active_heading_list = items;
};

PresentationControls.prototype.update_headingbox = function() {
    var self = this;
    this.headingscontrol.empty();
    jQuery.each(this.active_heading_list, function(i, item) {
                    var spaces = (new Array((item.level - 1)*3)).join("&nbsp;");
                    var caption = "";
                    var tag = item.tag.toLowerCase();
                    if (tag == 'row' || tag == 'column') {
                        caption = escapeHtml(item.name);
                    } else {
                        caption = tag + ": " + escapeHtml(item.name);
                    }
                    self.headingscontrol.append("<option class ='" + tag + "' value='" + i.toString() + "'>" + spaces + caption + "</option>");
    });
};

PresentationControls.prototype.retrieve_styles = function() {
    // Retrieve via AJAX
    var self = this;
    jQuery.getJSON(this.opts.retrieve_styles_url, {'template':this.opts.template,
                                                   'page_id':this.opts.page_id
                                                  },
                   function (data) {
                       self.with_good_data(data, function(value) {
                           self.available_styles = data.value;
                           self.build_classlist();
                       });
                   });
};


// The actual WYMeditor plugin:
WYMeditor.editor.prototype.semantic = function(options) {
    var wym = this;
    var c = new PresentationControls(wym, options);
};
