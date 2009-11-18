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

PresentationControls.prototype.setup_controls = function(container) {
    var id_prefix = "id_prescontrol_" + this.name + "_";
    var headingsbox_id = id_prefix + 'headings';
    var optsbox_id = id_prefix + 'optsbox';
    var headingsfilter_id = id_prefix + 'headingsfilter';
    var previewbutton_id = id_prefix + 'previewbutton';
    var previewbox_id = id_prefix + 'previewbox';
    var refresh_id = id_prefix + 'refresh';
    var newrowbutton_id = id_prefix + 'newrowbutton';
    var newcolbutton_id = id_prefix + 'newcolbutton';
    var removebutton_id = id_prefix + 'removebutton';
    var self = this;

    // Create elements
    container.after(
	"<div class=\"prescontrol\">" +
	"<table width=\"100%\" border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td width=\"50%\"><div class=\"prescontrolheadings\">Structure:<br/><select size=\"7\" id=\"" + headingsbox_id + "\"></select>" +
	"<br/><label><input type=\"checkbox\" id=\"" + headingsfilter_id + "\"> Headings only</label></div></td>" +
	"<td width=\"50%\"><div class=\"prescontroloptsboxcont\">Presentation choices:<div class=\"prescontroloptsbox\" id=\"" + optsbox_id + "\"></div>" +
        "<input type=\"submit\" value=\"New row\" id=\"" + newrowbutton_id  +"\" />" +
        "<input type=\"submit\" value=\"New column\" id=\"" + newcolbutton_id  +"\" />" +
        "<input type=\"submit\" value=\"Remove\" id=\"" + removebutton_id  +"\" />" +
        "</div></td></tr></table>" +
	"<table width=\"100%\" border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr>" +
	    "<td><input type=\"submit\" value=\"Refresh structure\" id=\"" + refresh_id + "\" /></td>" +
	    "<td><input type=\"submit\" value=\"Preview\" id=\"" + previewbutton_id + "\" /></td>" +
            "<td width=\"100%\"><div class=\"prescontrolerror\" id=\"" + id_prefix + "errorbox" + "\"></div></td></tr></table>" +
        "</div>");

    jQuery("body").append("<div style=\"position: absolute; display: none\" class=\"previewbox\" id=\"" + previewbox_id + "\">");

    this.optsbox = jQuery('#' + optsbox_id);
    this.headingscontrol = jQuery('#' + headingsbox_id);
    this.headingsfilter = jQuery('#' + headingsfilter_id);
    this.errorbox = jQuery('#' + id_prefix + "errorbox");
    this.previewbutton = jQuery('#' + previewbutton_id);
    this.previewbox = jQuery('#' + previewbox_id);
    this.refreshbutton = jQuery('#' + refresh_id);
    this.newrowbutton = jQuery('#' + newrowbutton_id);
    this.newcolbutton = jQuery('#' + newcolbutton_id);
    this.removebutton = jQuery('#' + removebutton_id);
    this.optsbox.css('height', this.headingscontrol.get(0).clientHeight.toString() + "px");

    // Initial set up
    this.retrieve_styles();
    // refresh_headings must come after separate_presentation
    this.separate_presentation(function() { self.refresh_headings(); });

    // Event handlers
    this.headingscontrol.change(function(event) {
				    self.update_optsbox();
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
    // Insert rewriting of HTML before the WYMeditor updates the textarea.
    jQuery(this.wym._options.updateSelector)
	.bind(this.wym._options.updateEvent, function(event) {
		  self.form_submit(event);
	      });

    // Other event handlers added in update_optsbox
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

PresentationControls.prototype.build_optsbox = function() {
    this.optsbox.empty();
    // Remove any tooltips
    jQuery(".orbitaltooltip-simplebox").unbind().remove();

    var self = this;
    jQuery.each(this.available_styles, function(i, item) {
	var val = flattenPresStyle(item);
	self.optsbox.append("<div><label><input type=\"checkbox\" value=\"" +
			    escapeHtml(val) + "\" /> " +
			    escapeHtml(item.verbose_name) +
			    "</label></div>");
	// Attach tooltip to label we just added:
	self.optsbox.find("input[value='" + val + "']").parent().each(function() {
	    var help = item.description;
	    if (help == "") {
		help = "(No help available)";
	    }
	    help = "<h1>" + escapeHtml(item.verbose_name) + "</h1>" + help;
            help = help + '<br/><hr/><p>Can be used on these elements:</p><p>' + item.allowed_elements.join(' ') + '</p>';
	    // Assign an id, because orbitaltooltip
            // doesn't work without it.
	    $(this).attr('id', 'id_optsbox_label_' + i);
            var inputitem = this;
            setTimeout(function() {
	        $(inputitem).orbitaltooltip({
	            orbitalPosition: 270,
		    // Small spacing means we can move onto the tooltip
                    // in order to scroll it if the help text has
		    // produced scroll bars.
		    spacing:         8,
		    tooltipClass: 	 'orbitaltooltip-simplebox',
		    html:            help
	        });
            }, 1000); // Delay, otherwise tooltips can end up in wrong position.
	});
    });
    // Stop the tooltips from getting in the way
    // - dismiss with a click.
    jQuery(".orbitaltooltip-simplebox").click(function(event) {
						  jQuery(this).hide();
					      });
};

PresentationControls.prototype.unbind_optsbox = function() {
    // Remove existing event handlers, reset state
    this.optsbox.find("input").unbind().removeAttr("checked").attr("disabled", true);
};

PresentationControls.prototype.get_heading_index = function() {
    var selected = this.headingscontrol.get(0).value;
    if (!selected) {
	return null;
    }
    return parseInt(selected, 10);
};

PresentationControls.prototype.update_optsbox = function() {
    var self = this;
    this.unbind_optsbox();
    // Currently selected heading?
    var headingIndex = self.get_heading_index();
    if (headingIndex == null) return;
    var sect = this.active_heading_list[headingIndex];
    var sect_id = sect.sect_id;
    var styles = this.presentation_info[sect_id];
    if (styles == null) {
	styles = new Array();
	this.presentation_info[sect_id] = styles;
    }
    this.optsbox.find("input").each(
	function(i, input) {
	    // Set state
	    var val = input.value;
            if (jQuery.inArray(sect.tag.toLowerCase(), self.available_styles[i].allowed_elements) != -1) {
                input.disabled = false;
            } else {
                input.disabled = true;
            }
	    jQuery.each(styles,
		function (j, style) {
		    if (flattenPresStyle(style) == val) {
			input.checked = true;
		    }
		});
	    // Add event handlers
	    // Change
	    jQuery(this).change(function(event) {
				    var style = expandPresStyle(input.value);
				    if (input.checked) {
					self.add_style(sect_id, style);
				    } else {
					self.remove_style(sect_id, style);
				    }
				    self.headingscontrol.get(0).focus();
			 });
	});
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
    this.unbind_optsbox();
    this.headingscontrol.empty();
    jQuery.each(this.active_heading_list, function(i, item) {
		    var spaces = (new Array((item.level - 1)*3)).join("&nbsp;");
                    var caption = "";
                    var tag = item.tag.toLowerCase();
                    if (tag == 'row' || tag == 'column') {
                        caption = "[" + escapeHtml(item.name) + "]";
                    } else {
                        caption = tag + ": " + escapeHtml(item.name);
                    }
		    self.headingscontrol.append("<option value='" + i.toString() + "'>" + spaces + caption + "</option>");
    });
};

PresentationControls.prototype.retrieve_styles = function() {
    // Retrieve via AJAX
    var self = this;
    jQuery.getJSON(this.opts.retrieve_styles_url, {},
		   function (data) {
		       self.with_good_data(data, function(value) {
			   self.available_styles = data.value;
			   self.build_optsbox();
		       });
		   });
};


// The actual WYMeditor plugin:
WYMeditor.editor.prototype.semantic = function(options) {
    var wym = this;
    var c = new PresentationControls(wym, options);
};
