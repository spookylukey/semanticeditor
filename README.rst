Semantic Editor
===============

Semantic Editor is a `Django CMS <http://www.django-cms.org/>`_ plugin for
text editing.  It allows you to edit the content of a page in a semantic
way, and then assign presentation and layout details to each section of the
text.  It supports complex column layouts using a simple set of controls
(new row, new column).

CSS classes are stored in the database, and can be limited to certain elements
(p, ul, li etc) and to certain templates.

This project is used as part of Arkestra by Cardiff University School of
Medicine, who conceived of the system.

Screen shots can be found at https://bitbucket.org/spookylukey/semanticeditor/wiki/Home

Installation
------------

See the installation instructions in INSTALL.rst

Usage
-----

After installation, when editing a page in Django-CMS you will have a plugin
type called 'Text/layout'. Choose this type of plugin and you will see an
enhanced text editor, based on WYMeditor. Down the right hand side you will see
'commands' and 'classes', as well the 'containers' that are provided by
WYMeditor.

The list of commands is built in to Semantic Editor, and allows columnar layouts
to be generated using simple commands like 'New row' and 'New column'. The
'preview' button allows you to test the layout that will be generated.

For the layout to work on your live site, you will need to include CSS in the
stylesheets that will correctly format the div structure into a set of columns.
Some basic CSS to start with is as follows::

    .row { clear: left; }
    .row .column { float: left; }
    .columns1 .column { width: 100%; }
    .columns2 .column { width: 50%; }
    .columns3 .column { width: 33%; }
    .columns4 .column { width: 25%; }
    .columns5 .column { width: 20%; }
    .columns6 .column { width: 16%; }

The list CSS classes that appear down the right hand side of the editor is
defined in the database. You can use the Django admin to add and edit the
'CssClass' objects and assign them to the different templates. You will have to
add the corresponding CSS to your stylesheets to actually provide the styling
for these classes.

With the CssClass objects, there is support for styles which can be applied to
columns to make them take up more than one column. For example, you might define
a style 'doublewidth', and set the 'Column count equivalent' to '2', and
ensuring that 'Allowed HTML elements' contained 'newcol'. You might then, for
example, add 3 columns to a layout by using the 'New column' command in the
editor. If you highlight the first column, you will be able to apply the
'doublewidth' class. In the generated output, the columns will be in a div with
'columns4' applied (not 'columns3'), and the first column will have
'doublewidth' applied. With appropriate CSS, you can now create a double width
column.

Internals - overview
--------------------

The aim is to have an editor in which content is edited semantically, and both
column layout and styling are applied separately.  However, in the database only
the combined HTML is stored.  So, we have the following situation:

HTML content is stored in the database something like::

    <div class="row columns2">
       <div class="column">
         <h1 class="fancy">Heading</h1>
         <p class="note bordered">Some text</p>
       </div>
       <div class="column doublewidth">
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
       {'newrow_h1_1': [] },               # specifies row before h1_1
       {'newcol_p_2': ['doublewidth'] },   # specifier col before p_2
                                           #  and styles for whole column
    ]

These two parts are then edited separately, i.e. the user does not see the
combined HTML while editing.  Before saving to the database, the editor does an
AJAX call to combine the two parts.  Note the use of the 'id' attributes are
added to help identify what the styling information belongs to -- these will be
removed before saving in the database.

Internals - WYMeditor extensions
--------------------------------

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

