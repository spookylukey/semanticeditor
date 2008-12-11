/*
 * Plugin for WYMEditor that provides an interface to allow sepataion
 * of presentation and content by allowing the user to select presentation
 * elements for each section.  Depends on a server-side backed to do
 * parsing and provide list of allowed CSS classes.
 */

function PresentationControls(wym) {
    this.name = wym._element.get(0).name;
    this.wym = wym;
    var container = jQuery(wym._box).find(".wym_area_bottom");
    this.available_styles = new Array();
    this.stored_headings = new Array();
    this.setup_controls(container);
}

/*
 * TODO
 * separate_presentation
 *  - called on setup
 * combine_presentation
 *  - called before teardown
 * retrieve_styles
 *  - called on setup
 * update_headingbox
 *  - called when new info about headings arrives
 * build_optsbox
 *  - called when information about available styles arrives
 *  - needs to create controls
 * update_optsbox
 *  - remove any existing event handlers
 *  - sets up control state from stored data
 *  - then add event handlers
 * optsbox event handlers
 *  - these need to store style data depending on what
 *    the user just changed
 * // wrappers for storing data:
 * add_style(heading, pres)
 * remove_style(heading, pres)
 * update_stored_headings
 *  - called when new info about headings arrives
 * current_heading
 */

function escapeHtml(html) {
    return html.replace(/&/g,"&amp;")
	.replace(/\"/g,"&quot;")
	.replace(/</g,"&lt;")
	.replace(/>/g,"&gt;");
}

PresentationControls.prototype.setup_controls = function(container) {
    var id_prefix = "id_prescontrol_" + this.name + "_";
    var headingsbox_id = id_prefix + 'headings';
    var optsbox_id = id_prefix + 'optsbox';
    var self = this;
    container.after(
	"<div class=\"prescontrol\">" +
	"<table width=\"100%\" border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td width=\"50%\"><div class=\"prescontrolheadings\">Headings:<br/><select size=\"7\" id=\"" + headingsbox_id + "\"></select></div></td>" +
	"<td width=\"50%\"><div class=\"prescontroloptsboxcont\">Presentation choices:<div class=\"prescontroloptsbox\" id=\"" + optsbox_id + "\"></div></div></td></tr></table>" +
	"<table width=\"100%\" border=\"0\" cellpadding=\"0\" cellspacing=\"0\"><tr><td><div class=\"prescontrolrefresh\"><input type=\"submit\" value=\"Refresh headings\" id=\"" + id_prefix + "refresh" + "\" /></div></td>" +
	"<td width=\"*\"><div class=\"prescontrolerror\" id=\"" + id_prefix + "errorbox" + "\"></div></td></tr></table>" +
        "</div>");

    this.optsbox = jQuery('#' + optsbox_id);
    this.headingscontrol = jQuery('#' + headingsbox_id);
    this.errorbox = jQuery('#' + id_prefix + "errorbox");
    // TODO - handler for error box to expand when clicked.
    this.optsbox.css('height', this.headingscontrol.get(0).clientHeight.toString() + "px");
    jQuery("#" + id_prefix + "refresh").click(function(event) {
						  self.refresh_headings();
						  return false;
					      });
    this.retrieve_styles();
    // Event handlers
    this.headingscontrol.change = function(event) {
	self.update_optsbox();
    };
};

PresentationControls.prototype.build_optsbox = function() {
    this.optsbox.empty();
    var self = this;
    jQuery.each(this.available_styles, function(i, item) {
	// TODO name, value
	// TODO - tooltip with description
	self.optsbox.append("<div style=\"clear: left;\"><div><label><input type=\"checkbox\" value=\"\" /> " + escapeHtml(item.verbose_name) + "</label></div></div>");
    });
};

// If data contains an error message, display to the user,
// otherwise clear the displayed error and perform the callback
PresentationControls.prototype.handle_error = function(data, callback) {
    if (data.result == 'ok') {
	this.clear_error();
	callback();
    } else {
	this.clear_error();
	// TODO - perhaps distinguish between a server error
	// and a user error
	this.show_error(data.message);
    }
};

PresentationControls.prototype.clear_error = function() {
    this.errorbox.empty();
};

PresentationControls.prototype.show_error = function(message) {
    this.errorbox.append(escapeHtml(message));
};

PresentationControls.prototype.refresh_headings = function() {
    var self = this;
    var html = this.wym.html();
    jQuery.post("/semantic/extract_headings/", { 'html':html },
	function(data) {
	    self.handle_error(data, function() {
		self.stored_headings = data.value;
		self.update_headingbox();
	    });
	}, "json");
};

PresentationControls.prototype.update_headingbox = function() {
    var self = this;
    this.headingscontrol.empty();
    jQuery.each(this.stored_headings, function(i, item) {
		    self.headingscontrol.append("<option value='" + i.toString() + "'>" + escapeHtml(item[1]) + "</option>");
    });
};

PresentationControls.prototype.retrieve_styles = function() {
    // Retrieve via AJAX
    // TODO - remove hardcoded URL
    var self = this;
    jQuery.getJSON("/semantic/retrieve_styles/", {},
		   function (data) {
		       // TODO - handle failure
		       if (data.result == 'ok') {
			   self.available_styles = data.value;
			   self.build_optsbox();
		       }
		   });
};


// The actual WYMeditor plugin:
WYMeditor.editor.prototype.semantic = function(options) {
    // TODO - options need to specify the AJAX callbacks
    // we are going to need.
    var wym = this;
    var c = new PresentationControls(wym);
};
