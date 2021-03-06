var testgroup;
var filter_req;

var showAll = function(err) {
  // if they cancelled, then just don't change anything:
  if (err instanceof CancelledError) { return }
  toggleMessage('none');
	
  var testgroupbox = document.getElementById("testgroup_id");
  for (var i=0; i<testgroupbox.options.length; i++) {
    var option = testgroupbox.options[i];
    option.style.display = '';
  }
  enableForm(formName);
};

var doFilterList = function(req) {
  var testgroups = req.responseText.split("\n");
  var testgroupbox = document.getElementById("testgroup_id");
  var alreadySeen = new Object;
  for (var i=0; i<testgroupbox.options.length; i++) {
    var testgroup = testgroupbox.options[i];
    var hide = 0;
    var id = testgroup.value;
    if (alreadySeen[id]) {
      hide = 1;
    } else {
      alreadySeen[id] = 1;
      if (testgroups.indexOf(id) == -1) {
        hide = 1;
      }
    }
    hide == 1 ? testgroup.style.display = 'none' : testgroup.style.display = '';
  }
  toggleMessage('none');
  enableForm(formName);
  disableModeButtons();
};

// filter the list by various criteria:
function filterList() {
  // they just changed the selection, so cancel any pending filter actions:
  if (filter_req instanceof Deferred && filter_req.fired == -1)
    filter_req.cancel();

  disableModeButtons();
  disableForm(formName);
  

  var productfilter = document.getElementById('product_filter');
  var branchfilter = document.getElementById('branch_filter');

  if (branchfilter.options[branchfilter.selectedIndex].value == '' &&
      productfilter.options[productfilter.selectedIndex].value == '') {
    // nothing to do here
    showAll();
    return;
  }

  toggleMessage('loading','Filtering testgroup list...');
  filter_req = doSimpleXMLHttpRequest('manage_testgroups.cgi', {
    searchTestgroupList: 1,
    product: (productfilter.options[productfilter.selectedIndex].value == '' ? '' : productfilter.options[productfilter.selectedIndex].value),
    branch: (branchfilter.options[branchfilter.selectedIndex].value == '' ? '' : branchfilter.options[branchfilter.selectedIndex].value)
  });
  // if something went wrong, just show all the tests:
  filter_req.addErrback(showAll);
  filter_req.addCallback(doFilterList);
}

function enableModeButtons() {
  document.getElementById("edit_testgroup_button").disabled=false;
  document.getElementById("clone_testgroup_button").disabled=false;
  document.getElementById("delete_testgroup_button").disabled=false;
}

function disableModeButtons() {
  document.getElementById("edit_testgroup_button").disabled=true;
  document.getElementById("clone_testgroup_button").disabled=true;
  document.getElementById("delete_testgroup_button").disabled=true;
}

function loadTestgroup(silent) {
  disableModeButtons();

  var testgroup_select = document.getElementById("testgroup_id");

  if (! testgroup_select ||
      testgroup_select.options[testgroup_select.selectedIndex].value=="") {
    disableModeButtons();
    document.getElementById('testgroup_display_div').style.display = 'none';
    document.getElementById('editform_div').style.display = 'none';
    disableForm('edit_testgroup_form');
    blankTestgroupForm('edit_testgroup_form');
    return false;
  } 

  var testgroup_id = testgroup_select.options[testgroup_select.selectedIndex].value;

  disableForm('edit_testgroup_form');
  if (!silent) {
    toggleMessage('loading','Loading Testgroup ID# ' + testgroup_id + '...');
  }
  var url = 'json.cgi?testgroup_id=' + testgroup_id;
  return fetchJSON(url,populateTestgroup,silent);
}

function populateTestgroup(data) {
  testgroup=data;
  document.getElementById('editform_testgroup_id').value = testgroup.testgroup_id;
  document.getElementById('testgroup_id_display').innerHTML = testgroup.testgroup_id;
  document.getElementById('testgroup_id_display_edit').innerHTML = testgroup.testgroup_id;
  document.getElementById('name').value = testgroup.name;
  document.getElementById('testgroup_name_display').innerHTML = testgroup.name;
  document.getElementById('testgroup_enabled_display').innerHTML = testgroup.enabled ? 'Yes' : 'No';
  document.getElementById('testgroup_creator_display').innerHTML = testgroup.creator_id.email ? testgroup.creator_id.email : "Not specified";
  document.getElementById('testgroup_creation_date_display').innerHTML = testgroup.creation_date;
  document.getElementById('testgroup_last_updated_display').innerHTML = testgroup.last_updated;

  var productBox = document.getElementById('product');
  var found_product = setSelected(productBox,testgroup.product_id.product_id);
  if (found_product == 1) {
    for (var i=0; i<products.length; i++) {
      if (products[i].product_id == testgroup.product_id.product_id) {
        document.getElementById('testgroup_product_name_display').innerHTML = products[i].name;
        continue;
      }
    }
  } else {
   document.getElementById('testgroup_product_name_display').innerHTML = '<em>No product set for this testgroup.</em>';
  }
  changeProduct();
  var branchBox = document.getElementById('branch');
  populateBranches(branchBox,productBox);
  var found_branch = setSelected(branchBox,testgroup.branch_id.branch_id);
  if (found_branch == 1) {
    for (var i=0; i<branches.length; i++) {
      if (branches[i].branch_id == testgroup.branch_id.branch_id) {
        document.getElementById('testgroup_branch_name_display').innerHTML = branches[i].name;
        continue;
      }
    }
  } else {
    document.getElementById('testgroup_branch_name_display').innerHTML = '<em>No branch set for this testgroup.</em>';
  }

  var enabled_em = document.getElementById('enabled')
  if (testgroup.enabled == 1) {
    enabled_em.checked = true;
    document.getElementById("testgroup_enabled_display").innerHTML = 'Yes';
  } else {
    enabled_em.checked = false;
    document.getElementById("testgroup_enabled_display").innerHTML = 'No';
 } 

  populateAllSubgroups();

  var selectBoxTestgroup = document.getElementById('testgroup_subgroups');
  selectBoxTestgroup.options.length = 0;
  for (var i=0; i<testgroup.subgroups.length; i++) {
    var optionText = testgroup.subgroups[i].name + ' (' + testgroup.subgroups[i].subgroup_id + ')'; 

    selectBoxTestgroup.options[selectBoxTestgroup.length] = new Option(optionText,
                                                     testgroup.subgroups[i].subgroup_id);
  }

  document.getElementById('creation_date').innerHTML = testgroup.creation_date;
  document.getElementById('last_updated').innerHTML = testgroup.last_updated;
  setSelected(document.getElementById('created_by'),testgroup.creator_id.user_id);

  document.getElementById('editform_div').style.display = 'none';
  document.getElementById('testgroup_display_div').style.display = 'block';
  enableModeButtons();
}

function blankTestgroupForm(formid) {
  blankForm(formid);
  updatePersistVars();
  document.getElementById('testgroup_id_display').innerHTML = '';
  document.getElementById('testgroup_name_display').innerHTML = '';
  document.getElementById('testgroup_enabled_display').innerHTML = '';
  document.getElementById('testgroup_creation_date_display').innerHTML = '';
  document.getElementById('testgroup_last_updated_display').innerHTML = '';
  var selectBoxAll = document.getElementById('subgroups_for_product');
  selectBoxAll.options.length = 0;
  selectBoxAll.options[selectBoxAll.length] = new Option("-No product selected-",
                                                             "");
  selectBoxAll.selectedIndex=-1;
  var selectBoxTestgroup = document.getElementById('testgroup_subgroups');
  selectBoxTestgroup.options.length = 0;
  selectBoxTestgroup.options[selectBoxTestgroup.length] = new Option("-No testgroup selected-","");
  selectBoxTestgroup.selectedIndex=-1;

  document.getElementById('testgroup_product_name_display').innerHTML = '';
  document.getElementById('testgroup_branch_name_display').innerHTML = '';

  testgroup = new Object();

  changeProduct();
  var productBox = document.getElementById('product');
  var branchBox = document.getElementById('branch');
  populateBranches(branchBox,productBox);
}

function switchToAdd() {
  disableModeButtons();
  document.getElementById('testgroup_display_div').style.display = 'none';
  blankTestgroupForm('edit_testgroup_form');
  document.getElementById('submit').value = 'Add Testgroup';
  document.getElementById('mode').value = 'add';
  document.getElementById('testgroup_id_display_edit').innerHTML = '<em>Automatically generated for a new Testgroup</em>';
  document.getElementById('creation_date').innerHTML = '<em>Automatically generated for a new Testgroup</em>';
  document.getElementById('last_updated').innerHTML = '<em>Automatically generated for a new Testgroup</em>';
  setSelected(document.getElementById('created_by'),current_user_id);
  enableForm('edit_testgroup_form');
  document.getElementById('editform_div').style.display = 'block';
}

function switchToEdit() {
  document.getElementById('submit').value = 'Submit Edits';
  document.getElementById('mode').value = 'edit';
  enableForm('edit_testgroup_form');
  document.getElementById('testgroup_display_div').style.display = 'none';
  document.getElementById('editform_div').style.display = 'block';
}

function populateAllSubgroups() {
  toggleMessage('loading','Narrowing Subgroup List...');
  try {
    var productBox = document.getElementById('product');
    var branchBox = document.getElementById('branch');
    var selectBoxAll = document.getElementById('subgroups_for_product');
    selectBoxAll.options.length = 0; 
    for (var i in subgroups) {
      if (subgroups[i].product_id != productBox.options[productBox.selectedIndex].value) {
        continue;
      }
      
      if (branchBox.selectedIndex >= 0) {

        if (branchBox.options[branchBox.selectedIndex].value != '' &&
            subgroups[i].branch_id != branchBox.options[branchBox.selectedIndex].value) {
	  continue;
        }
      } 
     
      var optionText = subgroups[i].name + ' (' + subgroups[i].subgroup_id + ')'; 
      selectBoxAll.options[selectBoxAll.length] = new Option(optionText,
                                                             subgroups[i].subgroup_id);
    }
    if (selectBoxAll.options.length == 0) {
      selectBoxAll.options[selectBoxAll.length] = new Option('-No Subgroups for this Product/Branch-','');
    }
  } catch (e) {
    // And do what exactly?
  }
  toggleMessage('none');
}  

function resetTestgroup() {
  if (document.getElementById('editform_testgroup_id').value != '') {
    populateTestgroup(testgroup);
    switchToEdit();   
  } else {
    switchToAdd();
  }
}

function checkFormContents(f) {
  return (
          checkString(f.name, 'Name') &&
          verifySelected(f.product, 'Product') &&
          verifySelected(f.branch, 'Branch') &&
          verifySelected(f.created_by, "Created By")
         );
}

function previewSubgroup(selectID) {
  var selectBox = document.getElementById(selectID);
  if (selectBox) {
    if (selectBox.selectedIndex >= 0) {
      if (selectBox.options[selectBox.selectedIndex].value != '') {
        window.open('manage_subgroups.cgi?subgroup_id=' + selectBox.options[selectBox.selectedIndex].value,
                    'subgroup_preview');
      }
    } else {
      toggleMessage('failure','No testgroup selected!');
    }
  }
}

function updatePersistVars() {
  var productBox = document.getElementById('product_filter');
  var branchBox = document.getElementById('branch_filter');
  if (productBox.selectedIndex) {
    var productPersist = document.getElementById('product_persist');
    productPersist.value = productBox.options[productBox.selectedIndex].value;
  }
  if (branchBox.selectedIndex) {
    var branchPersist = document.getElementById('branch_persist');
    branchPersist.value = branchBox.options[branchBox.selectedIndex].value;
  }
}

function disableCloneUpdateFields() {
  document.getElementById('old_name_regexp').disabled=true;
  document.getElementById('new_name_regexp').disabled=true;
  document.getElementById('update_names').setAttribute('class','disabled');
}

function enableCloneUpdateFields() {
  document.getElementById('old_name_regexp').disabled=false;
  document.getElementById('new_name_regexp').disabled=false;
  document.getElementById('update_names').setAttribute('class','');
}

var manageTestgroupsHelpTitle="Help with Managing Testgroups";
var manageTestgroupsHelpText="<p>The select box on the left contains all the subgroups for the chosen product, <strong><em>INCLUDING</em></strong> any subgroups already contained in the testgroup. You can use the <input type='button' value='&rArr;' disabled> button to add subgroups to the testgroup, and the <input type='button' value='&lArr;' disabled> button to remove subgroups from the testgroup. <strong>NOTE</strong>: neither of the actions will alter the list of subgroups on the left.</p><p>You can preview any subgroup from the left-hand select box by selecting the subgroup, and then clicking on  the 'Preview Subgroup' link below the select box. If more than one subgroup is selected, only the first subgroup will be previewed.</p><p>You can change the display order of subgroups within the testgroup using the <input type='button' value='&uArr;' disabled> and <input type='button' value='&dArr;' disabled> buttons to the right of the right-hand select box. Subgroups can be re-ordered singly or in groups by selecting multiple subgroups in the right-hand select box.</p>";
