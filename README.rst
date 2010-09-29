Semantic Editor
===============

Semantic editor is a Django CMS plugin for text editing. It allows you to edit a
web site in a semantic way, and then assign presentation and layout details to
each section of the text. It supports complex column layouts using a simple set
of controls (new row, new column).

CSS classes are stored in the database, and can be limited to certain elements
(p, ul, li etc) and to certain templates.

This project is used as part of Arkestra by Cardiff University School of
Medecine, who conceived of the system.

Overview
--------

The aim is to have an editor in which content is edited semantically, and both
column layout and styling are applied separately.  However, in the database only
the combined HTML is stored.  So, we have the following situation:

HTML content is stored in the database something like::

    <div class="row columns2">
       <div class="column">
         <h1 class="fancy">Heading</h1>
         <p class="note bordered">Some text</p>
       </div>
       <div class="column">
         <p>Some more text</p>
       </div>
    </div>

This is loaded into a custom editor in the browser which then immediately does
some AJAX calls to the server to decompose it into simplified HTML::

    <h1 id="h1_1">Heading</h1>
    <p id="p_1">Some text</p>
    <p id='p_2'>Some more text</p>

and an array of objects specifying presentation e.g.::

    [
       {'h1_1': ['fancy']},                # styles for the H1
       {'p_1':  ['note', 'bordered']},     # styles for the P
       {'newrow_h1_1': 'newrow' },         # specifies row before h1_1
       {'newrow_p_2': 'newcolum' },
    ]

These two parts are then edited separately, i.e. the user does not see the
combined HTML while editing.  Before saving to the database, the editor does an
AJAX call to combine the two parts.  Note the use of the 'id' attributes are
added to help identify what the styling information belongs to -- these will be
removed before saving in the database.

Depending on the GUI for editing the presentation info, the user may have to
press a 'refresh' button so that they can assign presentation info to newly
entered paragraphs and headings etc.  Newly entered paragraphs and headings will
obviously not have the 'id' attributes, so the HTML may have to be updated at
this point as well, so everything has an id.


WYMeditor extensions
--------------------

The Semantic Editor application provides its own version of WYMeditor.  This
is derived from the skins/templates found in django-cms2, with the following
customisations:

- name of the skin changed from 'django' to 'semanticeditor'.  This is
  necessary if we are to allow two different versions of WYMeditor on the
  same page, one using the normal WYMeditor + CMS controls, another with
  the full 'semantic editor' controls, for longer pieces of content.

- The skin.js file removes the 'classes' panel, since this is not needed
  and is replaced by dynamic elements.

- skins.css - added styling for additional presentation controls

- a WYMeditor plugin named 'semantic' has been added.  This implements
  most of the client side logic for this application.

- the editorwidget.html template has been changed.  In particular:

  - the skin has been changed to 'semanticeditor'
  - a call to wymeditor.semantic() has been added to set up the plugin.

- a new django widget 'SemanticEditor' has been created that inherits from
  the django 'WYMEditor' widget in django-cms2.  This is needed so that:

   - the WYMeditor 'semantic' plugin javascript file can be added to Media
   - our editorwdiget.html template can be used.

