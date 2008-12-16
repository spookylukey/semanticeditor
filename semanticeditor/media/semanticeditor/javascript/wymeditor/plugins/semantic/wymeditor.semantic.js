/*
 * Plugin for WYMEditor that provides an interface to allow sepataion
 * of presentation and content by allowing the user to select presentation
 * elements for each section.  Depends on a server-side backed to do
 * parsing and provide list of allowed CSS classes.
 */

function PresentationControls(wym, opts) {
    this.wym = wym;
    this.opts = opts;
    this.name = wym._element.get(0).name;
    // available_styles: an array of dictionaries corresponding to PresentationInfo objects
    this.available_styles = new Array();
    // stored_headings: an array of 2 elements arrays, [heading level, heading name]
    this.stored_headings = new Array();
    // active_heading_list - a possibly filtered version of stored_headings
    this.active_heading_list = new Array();
    // presentation_info: a dictionary of { heading name : [PresentationInfo] }
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
    var self = this;

    // Create elements
    container.after(
	"<div class=\"prescontrol\">" +
	"<table width=\"100%\" border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td width=\"50%\"><div class=\"prescontrolheadings\">Structure:<br/><select size=\"7\" id=\"" + headingsbox_id + "\"></select>" +
	"<br/><label><input type=\"checkbox\" id=\"" + headingsfilter_id + "\" checked=\"checked\"> Headings only</label></div></td>" +
	"<td width=\"50%\"><div class=\"prescontroloptsboxcont\">Presentation choices:<div class=\"prescontroloptsbox\" id=\"" + optsbox_id + "\"></div></div></td></tr></table>" +
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
    this.optsbox.css('height', this.headingscontrol.get(0).clientHeight.toString() + "px");

    // Initial set up
    this.retrieve_styles();
    this.refresh_headings();
    this.separate_presentation();
    this.update_optsbox();

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
    // Insert rewriting of HTML before the WYMeditor updates the textarea.
    jQuery(this.wym._options.updateSelector)
	.bind(this.wym._options.updateEvent, function(event) {
		  self.form_submit(event);
	      });

    // Other event handlers added in update_optsbox
};

// Splits the HTML into 'content HTML' and 'presentation'
PresentationControls.prototype.separate_presentation = function() {
    var self = this;
    jQuery.post(this.opts.separate_presentation_url, { html: self.wym.xhtml() } ,
		function(data) {
		    self.with_good_data(data,
			function(value) {
			    // Store the presentation
			    self.presentation_info = value.presentation;
			    // Update the HTML
			    self.wym.html(value.html);
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
	this.wym.html(data.value.html);
	// In case the normal WYMeditor update got called *before* this
	// event handler, we do another update.
	this.wym.update();
    } else {
	event.preventDefault();
	this.show_error(data.message);
	var pos = this.wym._box.offset();
	window.scrollTo(pos.left, pos.top);
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
	    // Assign an id, because orbitaltooltip
            // doesn't work without it.
	    $(this).attr('id', 'id_optsbox_label_' + i);
	    $(this).orbitaltooltip({
		orbitalPosition: 270,
		// Small spacing means we can move onto the tooltip
		// in order to scroll it if the help text has
		// produced scroll bars.
		spacing:         8,
		tooltipClass: 	 'orbitaltooltip-simplebox',
		html:            help
	    });
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

PresentationControls.prototype.update_optsbox = function() {
    var self = this;
    this.unbind_optsbox();
    // Currently selected heading?
    var selected = this.headingscontrol.get(0).value;
    if (!selected) {
	return;
    }
    var headingIndex = parseInt(selected, 10);
    var heading = this.active_heading_list[headingIndex][1];
    var styles = this.presentation_info[heading];
    if (styles == null) {
	styles = new Array();
	this.presentation_info[heading] = styles;
    }
    this.optsbox.find("input").each(
	function(i, input) {
	    // Set state
	    var val = input.value;
	    jQuery.each(styles,
		function (i, style) {
		    if (flattenPresStyle(style) == val) {
			input.checked = true;
		    }
		});
	    // Add event handlers
	    // Change
	    jQuery(this).change(function(event) {
				    var style = expandPresStyle(input.value);
				    if (input.checked) {
					self.add_style(heading, style);
				    } else {
					self.remove_style(heading, style);
				    }
				    self.headingscontrol.get(0).focus();
			 });
	});
    this.optsbox.find("input").removeAttr("disabled");
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

PresentationControls.prototype.add_style = function(heading, presinfo) {
    var styles = this.presentation_info[heading];
    styles.push(presinfo);
    this.presentation_info[heading] = jQuery.unique(styles);
};

PresentationControls.prototype.remove_style = function(heading, presinfo) {
    var styles = this.presentation_info[heading];
    styles = jQuery.grep(styles, function(item, i) {
			     return !(item.prestype == presinfo.prestype
				      && item.name == presinfo.name);
			 });
    this.presentation_info[heading] = styles;
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
    jQuery.post(this.opts.extract_headings_url, { 'html':html },
	function(data) {
	    self.with_good_data(data, function(value) {
		self.stored_headings = value;
		self.update_active_heading_list();
		self.update_headingbox();
	    });
	}, "json");
};

PresentationControls.prototype.update_active_heading_list = function() {
    var self = this;
    var items;
    if (this.headingsfilter.get(0).checked) {
	items = jQuery.grep(self.stored_headings,
                            function(item, idx) {
				return (item[2].toUpperCase()).match(/H\d/);
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
		    // item[0] is the heading level,
		    // item[1] is the heading name
		    var spaces = (new Array((item[0]-1)*2)).join("&nbsp;");
		    self.headingscontrol.append("<option value='" + i.toString() + "'>" + spaces + item[2].toUpperCase() + ": " + escapeHtml(item[1]) + "</option>");
    });
};

PresentationControls.prototype.retrieve_styles = function() {
    // Retrieve via AJAX
    // TODO - remove hardcoded URL
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
    // TODO - options need to specify the AJAX callbacks
    // we are going to need.
    var wym = this;
    var c = new PresentationControls(wym, options);
};
