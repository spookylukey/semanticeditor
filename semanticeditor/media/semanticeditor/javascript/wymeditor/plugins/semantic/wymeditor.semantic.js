/*
 * Plugin for WYMEditor that provides an interface to allow sepataion
 * of presentation and content by allowing the user to select presentation
 * elements for each section.  Depends on a server-side backed to do
 * parsing and provide list of allowed CSS classes.
 */

function PresentationControls(wym) {
    this.name = wym._element.get(0).name;
    var container = jQuery(wym._box).find(".wym_area_bottom");
    this.available_styles = new Array();
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
    return html.replace(/\"/g,"&quot;")
	.replace(/</g,"&lt;")
	.replace(/>/g,"&gt;")
	.replace(/&/g,"&amp;");
}

PresentationControls.prototype.setup_controls = function(container) {
    var id_prefix = "id_prescontrol_" + this.name + "_";
    var headingsbox_id = id_prefix + 'headings';
    var optsbox_id = id_prefix + 'optsbox';

    container.after("<div class=\"prescontrolheadings\">Headings:<br/><select size=\"7\" id=\"" + headingsbox_id + "\"></select></div>" +
		    "<div class=\"prescontroloptsboxcont\">Presentation choices:<div class=\"prescontroloptsbox\" id=\"" + optsbox_id + "\"></div></div>");

    this.optsbox = jQuery('#' + optsbox_id);
    this.headingscontrol = jQuery('#' + headingsbox_id);

    this.optsbox.get(0).style.height = this.headingscontrol.get(0).clientHeight.toString() + "px";

    this.retrieve_styles();
    // Event handlers
    this.headingscontrol.change = function(event) {
	this.update_optsbox();
    };
};

PresentationControls.prototype.build_optsbox = function() {
    this.optsbox.empty();
    var self = this;
    jQuery.each(this.available_styles, function(i, item) {
		    // TODO name, value
		    // TODO - tooltip with description
		    // TODO event handlers
		    self.optsbox.append("<div style=\"clear: left;\"><div><label><input type=\"checkbox\" value=\"\"> " + escapeHtml(item.verbose_name) + "</label></div></div>");
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
