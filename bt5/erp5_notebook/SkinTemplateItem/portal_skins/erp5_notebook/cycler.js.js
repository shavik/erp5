var Module=typeof pyodide!=="undefined"?pyodide:{};if(!Module.expectedDataFileDownloads){Module.expectedDataFileDownloads=0;Module.finishedDataFileDownloads=0}Module.expectedDataFileDownloads++;(function(){var loadPackage=function(metadata){var PACKAGE_PATH;if(typeof window==="object"){PACKAGE_PATH=window["encodeURIComponent"](window.location.pathname.toString().substring(0,window.location.pathname.toString().lastIndexOf("/"))+"/")}else if(typeof location!=="undefined"){PACKAGE_PATH=encodeURIComponent(location.pathname.toString().substring(0,location.pathname.toString().lastIndexOf("/"))+"/")}else{throw"using preloaded data can only be done on a web page or in a web worker"}var PACKAGE_NAME="cycler.data";var REMOTE_PACKAGE_BASE="cycler.data";if(typeof Module["locateFilePackage"]==="function"&&!Module["locateFile"]){Module["locateFile"]=Module["locateFilePackage"];err("warning: you defined Module.locateFilePackage, that has been renamed to Module.locateFile (using your locateFilePackage for now)")}var REMOTE_PACKAGE_NAME=Module["locateFile"]?Module["locateFile"](REMOTE_PACKAGE_BASE,""):REMOTE_PACKAGE_BASE;var REMOTE_PACKAGE_SIZE=metadata.remote_package_size;var PACKAGE_UUID=metadata.package_uuid;function fetchRemotePackage(packageName,packageSize,callback,errback){var xhr=new XMLHttpRequest;xhr.open("GET",packageName,true);xhr.responseType="arraybuffer";xhr.onprogress=function(event){var url=packageName;var size=packageSize;if(event.total)size=event.total;if(event.loaded){if(!xhr.addedTotal){xhr.addedTotal=true;if(!Module.dataFileDownloads)Module.dataFileDownloads={};Module.dataFileDownloads[url]={loaded:event.loaded,total:size}}else{Module.dataFileDownloads[url].loaded=event.loaded}var total=0;var loaded=0;var num=0;for(var download in Module.dataFileDownloads){var data=Module.dataFileDownloads[download];total+=data.total;loaded+=data.loaded;num++}total=Math.ceil(total*Module.expectedDataFileDownloads/num);if(Module["setStatus"])Module["setStatus"]("Downloading data... ("+loaded+"/"+total+")")}else if(!Module.dataFileDownloads){if(Module["setStatus"])Module["setStatus"]("Downloading data...")}};xhr.onerror=function(event){throw new Error("NetworkError for: "+packageName)};xhr.onload=function(event){if(xhr.status==200||xhr.status==304||xhr.status==206||xhr.status==0&&xhr.response){var packageData=xhr.response;callback(packageData)}else{throw new Error(xhr.statusText+" : "+xhr.responseURL)}};xhr.send(null)}function handleError(error){console.error("package error:",error)}var fetchedCallback=null;var fetched=Module["getPreloadedPackage"]?Module["getPreloadedPackage"](REMOTE_PACKAGE_NAME,REMOTE_PACKAGE_SIZE):null;if(!fetched)fetchRemotePackage(REMOTE_PACKAGE_NAME,REMOTE_PACKAGE_SIZE,function(data){if(fetchedCallback){fetchedCallback(data);fetchedCallback=null}else{fetched=data}},handleError);function runWithFS(){function assert(check,msg){if(!check)throw msg+(new Error).stack}Module["FS_createPath"]("/","lib",true,true);Module["FS_createPath"]("/lib","python3.6",true,true);Module["FS_createPath"]("/lib/python3.6","site-packages",true,true);Module["FS_createPath"]("/lib/python3.6/site-packages","__pycache__",true,true);Module["FS_createPath"]("/lib/python3.6/site-packages","cycler-0.10.0-py3.6.egg-info",true,true);function DataRequest(start,end,audio){this.start=start;this.end=end;this.audio=audio}DataRequest.prototype={requests:{},open:function(mode,name){this.name=name;this.requests[name]=this;Module["addRunDependency"]("fp "+this.name)},send:function(){},onload:function(){var byteArray=this.byteArray.subarray(this.start,this.end);this.finish(byteArray)},finish:function(byteArray){var that=this;Module["FS_createPreloadedFile"](this.name,null,byteArray,true,true,function(){Module["removeRunDependency"]("fp "+that.name)},function(){if(that.audio){Module["removeRunDependency"]("fp "+that.name)}else{err("Preloading file "+that.name+" failed")}},false,true);this.requests[this.name]=null}};var files=metadata.files;for(var i=0;i<files.length;++i){new DataRequest(files[i].start,files[i].end,files[i].audio).open("GET",files[i].filename)}function processPackageData(arrayBuffer){Module.finishedDataFileDownloads++;assert(arrayBuffer,"Loading data file failed.");assert(arrayBuffer instanceof ArrayBuffer,"bad input to processPackageData");var byteArray=new Uint8Array(arrayBuffer);var curr;if(Module["SPLIT_MEMORY"])err("warning: you should run the file packager with --no-heap-copy when SPLIT_MEMORY is used, otherwise copying into the heap may fail due to the splitting");var ptr=Module["getMemory"](byteArray.length);Module["HEAPU8"].set(byteArray,ptr);DataRequest.prototype.byteArray=Module["HEAPU8"].subarray(ptr,ptr+byteArray.length);var files=metadata.files;for(var i=0;i<files.length;++i){DataRequest.prototype.requests[files[i].filename].onload()}Module["removeRunDependency"]("datafile_cycler.data")}Module["addRunDependency"]("datafile_cycler.data");if(!Module.preloadResults)Module.preloadResults={};Module.preloadResults[PACKAGE_NAME]={fromCache:false};if(fetched){processPackageData(fetched);fetched=null}else{fetchedCallback=processPackageData}}if(Module["calledRun"]){runWithFS()}else{if(!Module["preRun"])Module["preRun"]=[];Module["preRun"].push(runWithFS)}};loadPackage({files:[{filename:"/lib/python3.6/site-packages/cycler.py",start:0,end:15959,audio:0},{filename:"/lib/python3.6/site-packages/__pycache__/cycler.cpython-36.pyc",start:15959,end:31999,audio:0},{filename:"/lib/python3.6/site-packages/cycler-0.10.0-py3.6.egg-info/top_level.txt",start:31999,end:32006,audio:0},{filename:"/lib/python3.6/site-packages/cycler-0.10.0-py3.6.egg-info/dependency_links.txt",start:32006,end:32007,audio:0},{filename:"/lib/python3.6/site-packages/cycler-0.10.0-py3.6.egg-info/PKG-INFO",start:32007,end:32720,audio:0},{filename:"/lib/python3.6/site-packages/cycler-0.10.0-py3.6.egg-info/SOURCES.txt",start:32720,end:33110,audio:0},{filename:"/lib/python3.6/site-packages/cycler-0.10.0-py3.6.egg-info/requires.txt",start:33110,end:33114,audio:0}],remote_package_size:33114,package_uuid:"49e462f0-cff7-482f-b8b2-7b414ac838db"})})();