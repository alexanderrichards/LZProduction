$(document).ready(function() {


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

