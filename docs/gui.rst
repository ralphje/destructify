================
GUI & Hex Viewer
================

The Destructify GUI is a method to easily analyze raw binary data, and how it is handled by the structures you have
defined.

Using the GUI is very easy::

    import destructify
    with open("raw.data", "rb") as f:
        destructify.gui.show(MyStructure, f)

The following screenshot shows how this might look if you are parsing a PNG file:

.. image:: gui.png
