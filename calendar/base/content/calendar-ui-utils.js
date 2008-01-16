/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 *
 * The contents of this file are subject to the Mozilla Public License Version
 * 1.1 (the "License"); you may not use this file except in compliance with
 * the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 *
 * Software distributed under the License is distributed on an "AS IS" basis,
 * WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
 * for the specific language governing rights and limitations under the
 * License.
 *
 * The Original Code is Sun Microsystems code.
 *
 * The Initial Developer of the Original Code is
 *   Philipp Kewisch <mozilla@kewis.ch>
 * Portions created by the Initial Developer are Copyright (C) 2008
 * the Initial Developer. All Rights Reserved.
 *
 * Contributor(s):
 *
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 *
 * ***** END LICENSE BLOCK ***** */

/**
 * Helper function for filling the form,
 * Set the value of a property of a XUL element
 *
 * @param aElement      ID of XUL element to set, or the element node itself
 * @param aNewValue     value to set property to ( if undefined no change is made )
 * @param aPropertyName OPTIONAL name of property to set, default is "value",
 *                        use "checked" for radios & checkboxes, "data" for
 *                        drop-downs
 */
function setElementValue(aElement, aNewValue, aPropertyName) {
    var undefined;

    if (aNewValue !== undefined) {
        if (typeof(aElement) == "string") {
            aElement = document.getElementById(aElement);
        }

        if (aNewValue === false) {
            try {
                aElement.removeAttribute(aPropertyName);
            } catch (e) {
                dump("setFieldValue: aElement.removeAttribute couldn't remove " +
                aPropertyName + " from " + aElement.localName + " e: " + e + "\n");
            }
        } else if (aPropertyName) {
            try {
                aElement.setAttribute(aPropertyName, aNewValue);
            } catch (e) {
                dump("setFieldValue: aElement.setAttribute couldn't set " +
                aPropertyName + " from " + aElement.localName + " to " + aNewValue +
                " e: " + e + "\n");
            }
        } else {
            aElement.value = aNewValue;
        }
     }
 }

/**
 * Helper function for getting data from the form,
 * Get the value of a property of a XUL element
 *
 * @param aElement      ID of XUL element to set, or the element node itself
 * @param propertyName  OPTIONAL name of property to set, default is "value",
 *                        use "checked" for radios & checkboxes, "data" for
 *                        drop-downs
 * @return newValue     Value of property
 *
 */
function getElementValue(aElement, aPropertyName) {
    if (typeof(aElement) == "string") {
        aElement = document.getElementById(aElement);
    }
    return aElement[aPropertyName || "value"];
}

/**
 * Unconditionally show the element (hidden attribute)
 *
 * @param aElement      ID of XUL element to set, or the element node itself
 */
function showElement(aElement) {
    setElementValue(aElement, false, "hidden");
}

/**
 * Unconditionally hide the element (hidden attribute)
 *
 * @param aElement      ID of XUL element to set, or the element node itself
 */
function hideElement(aElement) {
    setElementValue(aElement, "true", "hidden");
}

/**
 * Unconditionally enable the element (hidden attribute)
 *
 * @param aElement      ID of XUL element to set, or the element node itself
 */
function enableElement(aElement) {
    setElementValue(aElement, false, "disabled");
}

/**
 * Unconditionally disable the element (hidden attribute)
 *
 * @param aElement      ID of XUL element to set, or the element node itself
 */
function disableElement(aElement) {
    setElementValue(aElement, "true", "disabled");
}

/**
 * This function unconditionally disables the element for
 * which the id has been passed as argument. Furthermore, it
 * remembers who was responsible for this action by using
 * the given key (lockId). In case the control should be
 * enabled again the lock gets removed, but the control only
 * gets enabled if *all* possibly held locks have been removed.
 */
function disableElementWithLock(elementId,lockId) {

    // unconditionally disable the element.
    disableElement(elementId);

    // remember that this element has been locked with
    // the key passed as argument. we keep a primitive
    // form of ref-count in the attribute 'lock'.
    var element = document.getElementById(elementId);
    if (element) {
        if (!element.hasAttribute(lockId)) {
            element.setAttribute(lockId, "true");
            var n = parseInt(element.getAttribute("lock") || 0);
            element.setAttribute("lock", n + 1);
        }
    }
}

/**
 * This function is intended to be used in tandem with the
 * above defined function 'disableElementWithLock()'.
 * See the respective comment for further details.
 */
function enableElementWithLock(elementId, lockId) {

    var element = document.getElementById(elementId);
    if (!element) {
        dump("unable to find " + elementId + "\n");
        return;
    }

    if (element.hasAttribute(lockId)) {
        element.removeAttribute(lockId);
        var n = parseInt(element.getAttribute("lock") || 0) - 1;
        if (n > 0) {
            element.setAttribute("lock", n);
        } else {
            element.removeAttribute("lock");
        }
        if (n <= 0) {
            enableElement(elementId);
        }
    }
}

function processEnableCheckbox(checkboxId, elementId) {
    var checked = document.getElementById(checkboxId).checked;
    setElementValue(elementId, !checked && "true", "disabled");
}

/**
 *  Enable/disable button if there are children in a listbox
 */
function updateListboxDeleteButton(listboxId, buttonId) {
    var rowCount = document.getElementById(listboxId).getRowCount();
    setElementValue(buttonId, rowCount < 1 && "true", "disabled");
}

/**
 *  Update plural singular menu items
 */
function updateMenuLabels(lengthFieldId, menuId ) {
    var field = document.getElementById(lengthFieldId);
    var menu  = document.getElementById(menuId);

    // figure out whether we should use singular or plural
    var length = field.value;

    var newLabelNumber;

    // XXX This assumes that "0 days, minutes, etc." is plural in other languages.
    if ( (Number(length) == 0) || (Number(length) > 1) ) {
        newLabelNumber = "label2"
    } else {
        newLabelNumber = "label1"
    }

    // see what we currently show and change it if required
    var oldLabelNumber = menu.getAttribute("labelnumber");

    if (newLabelNumber != oldLabelNumber) {
        // remember what we are showing now
        menu.setAttribute("labelnumber", newLabelNumber);

        // update the menu items
        var items = menu.getElementsByTagName("menuitem");

        for (var i = 0; i < items.length; ++i) {
            var menuItem = items[i];
            var newLabel = menuItem.getAttribute(newLabelNumber);
            menuItem.label = newLabel;
            menuItem.setAttribute("label", newLabel);
        }

        // force the menu selection to redraw
        var saveSelectedIndex = menu.selectedIndex;
        menu.selectedIndex = -1;
        menu.selectedIndex = saveSelectedIndex;
    }
}

/**
 * Select value in menuList.  Throws string if no such value.
 */
function menuListSelectItem(menuListId, value) {
    var menuList = document.getElementById(menuListId);
    var index = menuListIndexOf(menuList, value);
    if (index != -1) {
        menuList.selectedIndex = index;
    } else {
        throw "menuListSelectItem: No such Element: "+value;
    }
}

/**
 * Find index of menuitem with the given value, or return -1 if not found.
 */
function menuListIndexOf(menuList, value) {
    var items = menuList.menupopup.childNodes;
    var index = -1;
    for (var i = 0; i < items.length; i++) {
        var element = items[i];
        if (element.nodeName == "menuitem") {
            index++;
        }
        if (element.getAttribute("value") == value) {
            return index;
        }
    }
    return -1; // not found
}