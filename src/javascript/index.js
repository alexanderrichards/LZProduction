$(document).ready(function() {
    var myChart = null;

    // DataTable setup
    /////////////////////////////////////////////////////
    $(".display").each(function(index){
	$(this).DataTable({ajax: {url: $(this).attr("data-source"),
                                  type: "GET",
                                  cache: true,
                                  // cant use success as DataTables uses that but this lets us
                                  // manipulate the data returned from the server prior to drawing.
                                  dataSrc: function(json) {
                                      // setup charts here.
                                      var charts_data = {}
                                      // without sort here the order of labels will be first come first serve which will mean that the pie chart will get different colours
                                      $.each(json.data.sort(function(a,b){return a.status.localeCompare(b.status)}), function(i, row) {
                                          if (!(row.status in charts_data)){
                                              charts_data[row.status] = 0;
                                          }
                                          charts_data[row.status]++;
                                          
                                      });
				      
                                      Chart.defaults.global.maintainAspectRatio = false;
                                      var keys = $.map(charts_data, function(value, key) { return key });
                                      var values = $.map(charts_data, function(value, key) { return value });
                                      var colours = $.map(Object.keys(charts_data), function(key, i) {return "hsl(" + (360.*i/Object.keys(charts_data).length) + ", 100%, 50%)"});
                                      if (myChart != null) {
                                          myChart.destroy();
                                      }
                                      myChart = new Chart($("#myChart"), {type: "pie",
                                                                          data: {labels: keys,
                                                                                 datasets: [{data: values,
                                                                                             backgroundColor: colours}]
                                                                                },
                                                                          responsive:true});
                                      return json.data;
                                  }
                                 },
                           order: [[4, "asc"], [5, "desc"], [1, "desc"]],
                           autoWidth: false,
                           columnDefs: [{ targets: "_all", className: "dt-body-left dt-head-left",
                                          render: function(data, type, row){
                                              return data.length > 40 ?
                                                  data.substr( 0, 40 ) +'…' :
                                                  data;
                                          }}],
                           columns: [{data:null, defaultContent: "<span class='glyphicon glyphicon-plus-sign text-primary details-control' style='cursor:pointer'></span>", orderable:false},
                                     {data: "id", title: "ID", className:"rowid", width:"5%"},
                                     {% if user.admin %}
                                     {data: "description", title: "Description", width: "50%"},
                                     {% else %}
                                     {data: "description", title: "Description", width: "60%"},
                                     {% endif %}
                                     {data: "sim_lead", title: "Sim Lead", width: "20%"},
                                     {data: "status", title: "Status", width: "7.5%", type: "request-status"},
                                     {data: "request_date", title: "Request Date", width: "7.5%"},
                                     {% if user.admin %}
                                     {data: "requester", title: "Requester", width: "10%"}
                                     {% endif %}
                                    ]
                          });
    });
    
    // Reload table ajax every 5 mins
    /////////////////////////////////////////////////////
    setInterval(function() {
	$("#tableBody").DataTable().ajax.reload();
    }, 300000);  // 5 mins

    // Custom sort order for request Status field
    /////////////////////////////////////////////////////
    $.fn.dataTable.ext.type.order['request-status-pre'] = function ( d ) {
	switch ( d ) {
        case 'Requested':    return 1;
        case 'Approved': return 2;
        case 'Submitted': return 3;
        case 'Running': return 4;
        case 'Failed':   return 5;
        case 'Completed':   return 6;
	}
	return 0;
    };
    
    // Table row details subtable show/hide
    /////////////////////////////////////////////////////
    $("#tableBody tbody").on("click", "tr td span.details-control", function() {
	var datatable = $("#tableBody").DataTable();
	var tr = $(this).closest("tr");
	var row = datatable.row(tr);
	var request_id = datatable.cell(row, $("td.rowid", tr)).data();
	if (row.child.isShown()){
            row.child.hide();
            //tr.removeClass("shown");
	}
	else{
	    $.ajax({url: '/details/' + request_id,
		   type: "GET",
		   success: function(data) {
		       row.child(data).show();
		   }});
            //tr.addClass("shown");
	}
	$(this).toggleClass("glyphicon-plus-sign")
	$(this).toggleClass("glyphicon-minus-sign")
	$(this).toggleClass("text-primary")
	$(this).toggleClass("text-danger")
    });
    /////////////////////////////////////////////////////

    // New request button
    /////////////////////////////////////////////////////
    $("#NewRequest").fancybox({
	type: "iframe",
	href: "/newrequest.html",
	title: "Submit New Request"
    });
    /////////////////////////////////////////////////////

    // Double click a row
    /////////////////////////////////////////////////////
    $("#tableBody tbody").on("dblclick", "tr", function(e){
	$.fancybox({
            type: "ajax",
            href: "/api/" + $("#tableBody").DataTable().cell($(this), $("td.rowid", this)).data()
	});
    });
    /////////////////////////////////////////////////////

    // Admins button
    /////////////////////////////////////////////////////
    $("#Admins").fancybox({
	type: "ajax",
	href: "/admins",
	title: "Admin Management",
	afterClose: function(){location.reload();}
    });
    /////////////////////////////////////////////////////
    
    // Table row selection
    /////////////////////////////////////////////////////
    var last_selected = 0;
    $("#tableBody tbody").on("click", "tr", function(e){
	var table_body = $("#tableBody tbody");
	var table_rows = $("#tableBody tbody tr");
        var new_selected = $(table_rows).index($(this));
	if (!e.ctrlKey && !e.shiftKey) {
	    $("tr.selected", $(table_body)).removeClass("selected");
        }
	else if (e.shiftKey) {
            if (new_selected < last_selected) {
                var length = $(table_rows).size() - 1;
                $(table_rows).slice(new_selected - length, last_selected - length - 1).addClass("selected");
            }
	    $(table_rows).slice(last_selected + 1, new_selected).addClass("selected");
	}
	$(this).toggleClass("selected");
        last_selected = new_selected;
    });
    /////////////////////////////////////////////////////
    
    // Context menu
    /////////////////////////////////////////////////////
    $("body").on("contextmenu", "#tableBody tbody tr", function(e) {
	e.preventDefault();
	if (!$(this).hasClass("selected")){
            $("#tableBody tbody tr.selected").removeClass("selected");
            $(this).addClass("selected");
	}
	
	var selected = $("#tableBody tbody tr.selected");
	if (selected.length > 1){
            $("#contextInfo").addClass("disabled");
            $("#contextCopy").addClass("disabled");
            $("#contextCopy span").removeClass("text-primary");
	}
	else{
            $("#contextCopy span").addClass("text-primary");
            $("#contextmenu ul li.disabled").removeClass("disabled")
	}
	
	var ids = [];
	var table = $("#tableBody").DataTable();
	selected.each(function() {
            ids.push(table.cell($(this), $("td.rowid", this)).data());
	});
	
	var contextmenu = $("#contextmenu");
	contextmenu.prop("ids", ids);
	contextmenu.css({left: e.pageX,
			 top: e.pageY});
	contextmenu.show();
    });
    
    $("html").click(function(e) {
	$("#contextmenu").hide();
    });
    
    /////////////////////////////////////////////////////
    
    // Context buttons
    /////////////////////////////////////////////////////
    $("#contextInfo").click(function() {
	if ($(this).hasClass("disabled")){ return false; }
	$.fancybox({
            type: "ajax",
            href: "/api/" + $("#contextmenu").prop("ids")
	});
    });
    
    $("#contextEdit").click(function() {
	if ($(this).hasClass("disabled")){ return false; }
	alert("Edit");
	$.fancybox({
            type: "iframe",
            href: "/editrequest.html",
            title: "Edit Request"
	});
    });
    
    $("#contextCopy").click(function() {
	if ($(this).hasClass("disabled")){ return false; }
	alert("COPY");
    });
    {% if user.admin %}
    $("#contextApprove").click(function() {
	if ($(this).hasClass("disabled")){ return false; }
	var ajax_calls = [];
	var ids = $("#contextmenu").prop("ids");
	for(var i in ids) {
            ajax_calls.push($.ajax({url: "/api/" + ids[i],
                                    type: "PUT",
                                    data: {"status": "Approved"}}));
	}
	$.when.apply(this, ajax_calls).done(function() {
            $("#tableBody").DataTable().ajax.reload();
            bootstrap_alert("Info!", "Approved " + ids.length + " request(s)", "alert-info");
	});
    });
    
    $("#contextDelete").click(function() {
	if ($(this).hasClass("disabled")){ return false; }
	var ajax_calls = [];
	var ids = $("#contextmenu").prop("ids");
	for(var i in ids) {
            ajax_calls.push($.ajax({url: "/api/" + ids[i],
                                    type: "DELETE"}));
	}
	$.when.apply(this, ajax_calls).done(function() {
            $("#tableBody").DataTable().ajax.reload();
            bootstrap_alert("Attention!", "Deleted "+ ids.length +" request(s)", "alert-danger");
	});
    });
    {% endif %}
    /////////////////////////////////////////////////////
    
    // Pressing Delete key
    /////////////////////////////////////////////////////
    $("body").keypress(function(e) {
	if (e.keyCode == 46){  //delete key
            var selected = $("#tableBody tbody tr.selected");
            if (!selected.length){ return; }
            bootbox.confirm("Really delete " + selected.length + " request(s)?", function(result) {
		if (!result){ return; }
		var ajax_calls = []
		var table = $("#tableBody").DataTable();
		selected.each(function() {
		    var id = table.cell($(this), $("td.rowid", this)).data();
		    ajax_calls.push($.ajax({url: "/api/" + id,
					    type: "DELETE"}));
		});
		$.when.apply(this, ajax_calls).done(function() {
		    table.ajax.reload();
		    bootstrap_alert("Attention!", "Deleted " + ajax_calls.length + " requests" , "alert-danger");
		});
            });
	}
    });
    /////////////////////////////////////////////////////
    
    
    // floating alertbox
    /////////////////////////////////////////////////////
    bootstrap_alert = function(status, message, level){
	// the below pops the notification into existence immediately
	// hence we add the hide to allow fadeIn once filled with html
	$("#notification").hide().html("\
<div class='alert alert-dismissible ###LEVEL###' role='alert'>\
<button type='button' class='close' data-dismiss='alert'>\
<span class='glyphicon glyphicon-remove-sign'></span>\
</button>\
<strong>###STATUS###</strong> ###MESSAGE###\
</div>".replace("###LEVEL###", level)
				       .replace("###MESSAGE###", message)
				       .replace("###STATUS###", status));
	$("#notification").fadeIn("slow").delay(2000).fadeOut("slow");
    };
    
    $("#testbutton").click(function(){
	bootstrap_alert("Danger!", "hello world", "alert-warning");
    });  
});
