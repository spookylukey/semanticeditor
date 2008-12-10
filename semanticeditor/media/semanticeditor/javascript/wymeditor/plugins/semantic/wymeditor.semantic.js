/*
 * Plugin for WYMEditor that provides an interface to allow sepataion
 * of presentation and content by allowing the user to select presentation
 * elements for each section.  Depends on a server-side backed to do
 * parsing and provide list of allowed CSS classes.
 */

function PresentationControls(wym) {
    this.name = wym._element.get(0).name;
    var container = jQuery(wym._box).find(".wym_area_bottom");
    var id_prefix = "id_prescontrol_" + this.name + "_";
    this.headingsbox_id = id_prefix + 'headings';
    this.optsbox_id = id_prefix + 'optsbox';
    this.setup_controls(container);
}

/*
 * TODO
 * separate_presentation
 *  - called on setup
 * combine_presentation
 *  - called before teardown
 * retrieve_style
 *  - called on setup
 * update_headingbox
 *  - called when new info about headings arrives
 * update_optsbox
 *  - needs to create controls
 *  - then set them up from stored data
 *  - then add event handlers
 * // wrappers for storing data:
 * add_style(heading, pres)
 * remove_style(heading, pres)
 * update_stored_headings
 *  - called when new info about headings arrives
 */

PresentationControls.prototype.setup_controls = function(container) {
    container.after("<div class=\"prescontrolheadings\">Headings:<br/><select size=\"5\" id=\"" + this.headingsbox_id + "\"></select></div>" +
		    "<div class=\"prescontroloptsboxcont\">Presentation choices:<div class=\"prescontroloptsbox\" id=\"" + this.optsbox_id + "\"></div></div>");
    // Event handlers
    this.headingscontrol.change = function(event) {
	this.update_optsbox();
    };
};

PresentationControls.prototype.optsbox = function() {
    return jQuery('#' + this.optsbox_id);
};

PresentationControls.prototype.headingscontrol = function() {
    return jQuery('#' + this.headingscontrol);
};

// The actual WYMeditor plugin:
WYMeditor.editor.prototype.semantic = function(options) {
    // TODO - options need to specify the AJAX callbacks
    // we are going to need.
    var wym = this;
    var c = new PresentationControls(wym);
};
