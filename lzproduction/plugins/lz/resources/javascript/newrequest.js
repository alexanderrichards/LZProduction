$(document).ready(function() {

  $(".toggle").change(function(){
    $(".togglable[toggle~='" + this.id + "']").prop("disabled", !this.checked);
    $("select[toggle='" + this.id + "']").selectpicker("refresh");
    if (!this.checked){
      $(".togglable[toggleoff~='" + this.id + "']").prop("disabled", true);
    }
    else if (this.checked){
      $(".togglable[toggleon~='" + this.id + "']").prop("disabled", false);
    }
  });

  $.ajax({url: "/tags",
          type: "GET",
          success: function(result) {
                     $("#tags").html(result);
                     $("#tags").selectpicker("refresh");
                   }
  });

  $.ajax({url: "/appversion/TDRAnalysis",
          type: "GET",
          success: function(result) {
                     $("#reduction_version").html(result);
                     $("#reduction_version").selectpicker("refresh");
                   }
  });

  $.ajax({url: "/appversion/fastNEST",
          type: "GET",
          success: function(result) {
                     $("#fastnest_version").html(result);
                     $("#fastnest_version").selectpicker("refresh");
                   }
  });

  $.ajax({url: "/appversion/DER",
          type: "GET",
          success: function(result) {
                     $("#der_version").html(result);
                     $("#der_version").selectpicker("refresh");
                   }
  });

  $.ajax({url: "/appversion/LZap",
          type: "GET",
          success: function(result) {
                     $("#lzap_version").html(result);
                     $("#lzap_version").selectpicker("refresh");
                   }
  });

  $("#tags").change(function() {
    $.ajax({url: "/tags",
            type: "GET",
            data: {tagid: $(this).val(),
                   app: $("#app").val()},
            success: function(result) {
                       $("#macros").html(result);
                       $("#macros").prop("disabled", false);
                       $("#macros").selectpicker("refresh");
                     }
            });
  });


  $("#app").change(function() {
    var app_version = $("#app_version");
    $.ajax({url: "/appversion/" + $("#app option:selected").text(),
            type: "GET",
            success: function(result) {
                       app_version.html(result);
                       app_version.prop("disabled", false);
                       app_version.selectpicker("refresh");
                     }
    });
    app_version.selectpicker("refresh");
    var tags = $("#tags");
    if (tags.val()){
        $.ajax({url: "/tags",
                type: "GET",
                data: {tagid: tags.val(),
                       app: $(this).val()},
                success: function(result) {
                           $("#macros").html(result);
                           $("#macros").selectpicker("refresh");
                         }
                });
    }
  });

  $("#add").click(function() {
    if ($("#macros option:selected").length < 1) {
      //alert("Must select a macro from the list first.");
      return false;
    }
    if ($("#njobs").val() == "") {
      alert("Must specify the number of jobs/files");
      return false;
    }
    if ($("#nevents").val() == "") {
      alert("Must specify the number of beam on events");
      return false;
    }
    if ($("#seed").val() == "") {
      alert("Must specify the initial seed");
      return false;
    }

    var sel_list = $("#selected_macros");
    $("#macros :selected").each(function(i, selected) {
        var njobs = $("#njobs").val();
        var nevents = $("#nevents").val();
        var seed = $("#seed").val();
        sel_list.append($("<option>", { text: [selected.value, njobs, nevents, seed].join(" "),
                                        path: selected.getAttribute("path"),
                                        njobs: $("#njobs").val(),
                                        nevents: $("#nevents").val(),
                                        seed: $("#seed").val() }));
    });
    sel_list.prop("disabled", false);
  });

  $("#remove").click(function() {
    var selected = $("#selected_macros");
    $("option:selected", selected).remove();
    if ($("option", selected).length < 1) {
        selected.prop("disabled", true);
    }
  });

  $("form").submit(function(event){
    // stop form submitting normally
    // could just let it submit normally if didn't need asynchronous ajax functionality
    event.preventDefault();

    // switch all options in the selected list to selected so that we
    // can serialize them
    $("#selected_macros option").prop("selected", true);
    $("#selected_macros option").each(function(i, selected) {
         selected.value = [selected.getAttribute("path"),
                           selected.getAttribute("njobs"),
                           selected.getAttribute("nevents"),
                           selected.getAttribute("seed")].join(" ");
    });

// the below waited to close the fancybox till after the table refreshed and after the ajax call
// completed. This introduced a noticeable delay
    parent.$.fancybox.close();
    $.ajax({url: this.action,  // this is the javascript this not JQuery object $(this)
            type: this.method,
//            data: $(this).serialize(),
            data: JSON.parse(JSON.stringify($(this).serializeArray())),
            success: function(result){
		       parent.$("#tableBody").DataTable().ajax.reload();
//                       parent.$.fancybox.close();
		       parent.bootstrap_alert("Success!", "Request added", "alert-success");
                       // by iteself, $ = jQuery.
                       // i.e. could use in the html onclick="parent.jQuery.fancybox.close();"
                    }
    });
//    parent.$.fancybox.close();
//    $.when($.ajax({url: this.action, type: this.method, data: $(this).serialize()})).done(function() {
//        parent.$("#tableBody").DataTable().ajax.reload();
//        parent.bootstrap_alert("Success!", "Request added", "alert-success");
//    });
  });

});