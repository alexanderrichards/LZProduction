
    // Table row details subtable show/hide
    /////////////////////////////////////////////////////
    function formatoutput(parametricjob){
	var output = '';
	if (parametricjob.sim_lfn_outputdir != null){
	    output = output.concat(parametricjob.sim_lfn_outputdir + "<br>");
	}
	if (parametricjob.mctruth_lfn_outputdir != null){
	    output = output.concat(parametricjob.mctruth_lfn_outputdir + "<br>");
	}
	if (parametricjob.reduction_lfn_outputdir != null){
	    output = output.concat(parametricjob.reduction_lfn_outputdir + "<br>");
	}
	if (parametricjob.der_lfn_outputdir != null){
	    output = output.concat(parametricjob.der_lfn_outputdir + "<br>");
	}
	if (parametricjob.lzap_lfn_outputdir != null){
	    output = output.concat(parametricjob.lzap_lfn_outputdir + "<br>");
	}
	return output;
    }

    function table_order_func(){
        return [[1, "desc"]];
    }

    function table_columns_func(){
        return [{data:null, defaultContent: "<span class='glyphicon glyphicon-plus-sign text-primary details-control' style='cursor:pointer'></span>", orderable:false},
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
                                    ];
    }

    function parametricjobs_preprocess(){
        var return_data = new Array();
        var data = json.data
	    for(var i=0;i< data.length; i++){
	        return_data.push({'macro': data[i].macro,
							  'njobs': data[i].njobs,
							  'nevents': data[i].nevents,
							  'seed': data[i].seed,
							  'output': formatoutput(data[i]),
							  'status': data[i].reschedule? 'Rescheduled': data[i].status,
							  'progress': formatprogress(data[i]),
							  'reschedule': data[i].status == 'Failed'? formatreschedule(data[i]): ''
							  })
		}
		return return_data;
    }

    function parametricjobs_columns(){
        return [{ data: 'macro', title: 'Macro' },
				{ data: 'njobs', title: 'NJobs' },
				{ data: 'nevents', title: 'NEvents' },
				{ data: 'seed', title: 'Seed' },
				{ data: 'output', title: 'Output' },
				{ data: 'status', title: 'Status' },
				{ data: 'progress', title: 'Progress' },
				{ data: 'reschedule', orderable: false }
                ];
    }

    function parametricjobs_order(){
        return [[5, 'desc']];
    }