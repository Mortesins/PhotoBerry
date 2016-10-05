/***
 Software for collecting data from PV energy meters
 Copyright (C) 2014 Axel Bernardinis <abernardinis@hotmail.com>

 This program is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program. If not, see <http://www.gnu.org/licenses/>.
***/


var photoBerry = angular.module('PhotoBerry',['ngRoute','ngTable','mgcrea.ngStrap']);

photoBerry.config(['$routeProvider',function($routeProvider) {
   $routeProvider
      .when('/home', {
         templateUrl : 'static/partials/home.html',
         controller  : 'homeController'
      })
      .when('/tabellaGiornaliera', {
         templateUrl : 'static/partials/tabellaGiornaliera.html',
         controller  : 'tabellaGiornalieraController'
      })
      .when('/tabellaMensile', {
         templateUrl : 'static/partials/tabellaMensile.html',
         controller  : 'tabellaMensileController'
      })
      .when('/graficoGiornaliero', {
         templateUrl : 'static/partials/graficoGiornaliero.html',
         controller  : 'graficoGiornalieroController'
      })
      .when('/graficoPotenza', {
         templateUrl : 'static/partials/graficoPotenza.html',
         controller  : 'graficoPotenzaController'
      })
      .when('/istantaneo', {
         templateUrl : 'static/partials/istantaneo.html',
         controller  : 'istantaneoController'
      })
      .otherwise({
         redirectTo: '/home'
      });
}]);

photoBerry.controller("homeController", function($scope) {

});

photoBerry.controller("tabellaGiornalieraController",
                        [  "$scope",
                           "$http",
                           "ngTableParams",
                           "minDateRequest",
                           "toStringForAJAX", 
               function ($scope,
                           $http,
                           ngTableParams,
                           minDateRequest,
                           toStringForAJAX) 
{
   // FUNCTIONS
   $scope.request = function ()
   {
      if ($scope.selezione == "singoloGiorno")
         $scope.giornoFine = $scope.giornoInizio;
      $http.get
         (
            "/giornalieroTabella",
            { 
               params: 
               {
                  giorno_inizio : toStringForAJAX($scope.giornoInizio),
                  giorno_fine   : toStringForAJAX($scope.giornoFine)
               }
            }
         )
         .success( function (data)
            {
               $scope.showTabella = true;
               $scope.dati = data["datiGiornata"];
            }
         ).error( function (data)
            {
               alert("ERRORE");
            }
         );
   }
   // PARAMETERS
   $scope.title = "Tabella Giornaliera";
   $scope.selezione = "singoloGiorno";
   $scope.labelGiornoInizio = {"singoloGiorno":"Giorno","giorniMultipli":"Giorno Inizio"};
   var today = new Date();
   $scope.maxDate = new Date(today.getFullYear(),today.getMonth(),today.getDate()-1);
   $scope.giornoInizio = $scope.maxDate;
   $scope.giornoFine = $scope.maxDate;
   $scope.minDate = new Date(2014,11,8);//getMinDate; // mese parte con 0
   $scope.dati = [];// inizializzo array json request
   $scope.tableParams = new ngTableParams({count:$scope.dati.length},{counts:[]});
   
   // INIT
   minDateRequest.success(function (data) 
      {
         $scope.minDate = new Date(Date.parse(data.dataMinima)); 
         $scope.minDate.setDate($scope.minDate.getDate() - 1 );  // per qualche strano motivo, dipende dai settaggi del DatePicker
      }
   );
}]);

photoBerry.controller("tabellaMensileController",
                        [  "$scope",
                           "$http",
                           "ngTableParams",
                           "minDateRequest",
                           "anniMesiConstructor",
                           "numeriMesi", 
               function ($scope,
                           $http,
                           ngTableParams,
                           minDateRequest,
                           anniMesiConstructor,
                           numeriMesi) 
{
   // FUNCTIONS
   $scope.request = function ()
   {
      $http.get
         (
            "/mensileTabella",
            { 
               params: 
               {
                  mese_inizio : numeriMesi($scope.meseInizio),//$scope.numeriMesi[$scope.meseInizio],
                  anno_inizio : $scope.annoInizio,
                  mese_fine   : numeriMesi($scope.meseFine),//$scope.numeriMesi[$scope.meseFine],
                  anno_fine   : $scope.annoFine
               }
            }
         )
         .success( function (data)
            {
               $scope.showTabella = true;
               $scope.dati = data["datiMese"];
            }
         ).error( function (data)
            {
               alert("ERRORE");
            }
         );
   }
   $scope.cambiaMesiSelezionabili = function (inizioOfine) 
   {
      //console.log("cambiamesi");
      var i = 0;
      if (inizioOfine == "inizio")
      {
         while ($scope.anniMesi[i++]["anno"] != $scope.annoInizio);
         i--;
         $scope.mesiSelezionabiliInizio = $scope.anniMesi[i]["mesi"];
         $scope.meseInizio = $scope.mesiSelezionabiliInizio[0];
      }
      else
      {
         while ($scope.anniMesi[i++]["anno"] != $scope.annoFine);
         i--;
         $scope.mesiSelezionabiliFine = $scope.anniMesi[i]["mesi"];
         $scope.meseFine = $scope.mesiSelezionabiliFine[$scope.mesiSelezionabiliFine.length - 1]; // non va bene 0
      }
   }
   $scope.cambiatoAnnoInizio = function ()
   {
      //console.log("cambiatoAnnoInizio");
      if ($scope.annoInizio > $scope.annoFine)
      {
         $scope.annoFine = $scope.annoInizio;
         $scope.cambiaMesiSelezionabili("fine");
      }
      $scope.cambiatoMeseInizio();
   }
   $scope.cambiatoMeseInizio = function ()
   {
      //console.log("cambiatoMeseInizio");
      if ( ($scope.annoInizio == $scope.annoFine) && (numeriMesi($scope.meseInizio) > numeriMesi($scope.meseFine)) )
      {
         $scope.meseFine = $scope.meseInizio;
      }
   }
   $scope.cambiatoAnnoFine = function ()
   {
      //console.log("cambiatoAnnoFine");
      if ($scope.annoFine < $scope.annoInizio)
      {
         $scope.annoInizio = $scope.annoFine;
         $scope.cambiaMesiSelezionabili("inizio");
      }
      $scope.cambiatoMeseFine();
   }
   $scope.cambiatoMeseFine = function ()
   {
      //console.log("cambiatoMeseFine");
      if ( ($scope.annoInizio == $scope.annoFine) && (numeriMesi($scope.meseFine) < numeriMesi($scope.meseInizio)) )
      {
         $scope.meseInizio = $scope.meseFine;
      }
   }
   
   // PARAMETERS
   $scope.title = "Tabella Mensile";
   //$scope.minDate = new Date(2014,11,7); // mese parte con 0
   $scope.dati = [];// inizializzo array json request
   $scope.tableParams = new ngTableParams({count:$scope.dati.length},{counts:[]});
   $scope.mesiSelezionabiliInizio = [];
   $scope.mesiSelezionabiliFine = [];
   $scope.anniMesi = [];

   // INIT
	minDateRequest.success(function (data) 
      {
         $scope.minDate = new Date(Date.parse(data.dataMinima)); 
         //$scope.minDate.setDate($scope.minDate.getDate() - 1 );  // per qualche strano motivo, dipende dai settaggi del DatePicker

         $scope.anniMesi = anniMesiConstructor($scope.minDate,includiMeseInCorso=false);
         $scope.annoInizio = $scope.anniMesi[0]["anno"];
         $scope.annoFine = $scope.anniMesi[0]["anno"];
         $scope.cambiaMesiSelezionabili("inizio");
         $scope.cambiaMesiSelezionabili("fine");
      }
   );
 
}]);

photoBerry.controller("graficoGiornalieroController",
                        [  "$scope",
                           "$http",
                           "minDateRequest",
                           "anniMesiConstructor",
                           "barGraph",
                           "$window",
                           "numeriMesi", 
                  function ($scope,
                           $http,
                           minDateRequest,
                           anniMesiConstructor,
                           barGraph,
                           $window,
                           numeriMesi
                           ) 
{
   // FUNCTIONS
   $scope.request = function ()
   {
      var windowSize = $window.innerWidth;
      //console.log("request");
      if ($scope.graficoMese != numeriMesi($scope.mese) || $scope.graficoAnno != $scope.anno)
      {
         $http.get
            (
               "/giornalieroGrafico",
               { 
                  params: 
                  {
                     mese : numeriMesi($scope.mese),
                     anno : $scope.anno
                  }
               }
            )
            .success( function (data)
               {
                  var tmp = data.giornateDelMese;
                  $scope.removeGrafico()
                  // per non ridisegnare lo stesso grafico
                  $scope.graficoMese = numeriMesi($scope.mese);
                  $scope.graficoAnno = $scope.anno;
                  barGraph(tmp,"potenza",d3.select("#barGraphPotenza"),windowSize*0.95);
                  barGraph(tmp,"produzione",d3.select("#barGraphProduzione"),windowSize*0.95);
               }
            ).error( function (data)
               {
                  alert("ERRORE");
               }
            );
      }
   }
   $scope.cambiaMesiSelezionabili = function () 
   {
      //console.log("cambiamesi");
      var i = 0;
      while ($scope.anniMesi[i++]["anno"] != $scope.anno);
      i--;
      $scope.mesiSelezionabili = $scope.anniMesi[i]["mesi"];
      $scope.mese = $scope.mesiSelezionabili[0];
   }
   $scope.removeGrafico = function()
   {
      (angular.element(document.querySelector('#barGraphPotenza'))).empty();
      (angular.element(document.querySelector('#barGraphProduzione'))).empty();
      (angular.element(document.querySelector('.d3-tip'))).remove();
      (angular.element(document.querySelector('.d3-tip'))).remove();
      $scope.graficoMese = 0;
      $scope.graficoAnno = 0;
   }
   
   // PARAMETERS
   $scope.title = "Grafico Giornaliero";
   $scope.minDate = new Date(2014,4,7); // mese parte con 0
   $scope.mesiSelezionabili = [];
   $scope.anniMesi = [];

   // INIT
   minDateRequest.success(function (data) 
      {
         $scope.minDate = new Date(Date.parse(data.dataMinima)); 
         $scope.anniMesi = anniMesiConstructor($scope.minDate,includiMeseInCorso=true);
         $scope.anno = $scope.anniMesi[0]["anno"];
         $scope.cambiaMesiSelezionabili();
      }
   );

}]);

photoBerry.controller("graficoPotenzaController",
                        [  "$scope",
                           "$http",
                           "minDateRequest",
                           "toStringForAJAX",
                           "lineGraph", 
                           "createDateFromTimeString",
               function ($scope,
                           $http,
                           minDateRequest,
                           toStringForAJAX,
                           lineGraph,
                           createDateFromTimeString
                           ) 
{
   // FUNCTIONS
   $scope.request = function ()
   {  
      $http.get
         (
            "/potenzaGrafico",
            { 
               params: 
               {
                  giorno : toStringForAJAX($scope.giorno),
               }
            }
         )
         .success( function (data)
            {
               $scope.dati = data["potenze"];
               for (i=0;i<$scope.dati.length;i++)
               {
                  $scope.dati[i].ora = createDateFromTimeString($scope.dati[i].ora,$scope.giorno);
               }
               lineGraph(giaDisegnato,$scope.dati,d3.select('#lineGraphPotenza'),width,height);
               $scope.showGrafico = true;
               giaDisegnato = true;
            }
         ).error( function (data)
            {
               alert("ERRORE: dati non disponibili");
            }
         );
   }
   
   // PARAMETERS
   $scope.title = "Grafico Potenza";
   var today = new Date();
   $scope.maxDate = new Date(today.getFullYear(),today.getMonth(),today.getDate());
   $scope.giorno = $scope.maxDate;
   $scope.minDate = new Date(2014,11,8);//getMinDate; // mese parte con 0
   var width = 1200;
   var height = 650;
   var giaDisegnato = false;
   
   // INIT
   minDateRequest.success(function (data) 
      {
         $scope.minDate = new Date(Date.parse(data.dataMinima)); 
         $scope.minDate.setDate($scope.minDate.getDate() - 1);  // per qualche strano motivo, dipende dai settaggi del DatePicker
      }
   );
   
}]);

photoBerry.controller("istantaneoController", 
                        [
                           "$scope",
                           "$http",
                           "graficoIstantaneo",
                           "redrawGraph",
                           "$window",
                           //"$q",
                           "$location",
               function ($scope,
                           $http,
                           graficoIstantaneo,
                           redrawGraph,
                           $window,
                           //$q,
                           $location
                           )
{
   // FUNCTIONS
   /*** ONLY FOR TESTING ***/
  // $scope.redrawGraph = function () { redrawGraph($scope.potenza,widthMax,potenzaMax); };
   /************************/
   var getValue = function ()
   {
      //console.log("getValue");
      $http.jsonp("http://"+String($location.host())+":8001/?callback=JSON_CALLBACK")
         .success( function (data)
            {
               $scope.potenza = data.potenza;
               redrawGraph($scope.potenza,widthMax,potenzaMax);
               if (data.potenza == -1)
                  setTimeout(getValue,60000); // se e' spento provo tra un minuto
               else
                  getValue();
            })
         .error(function (data)
            {
               console.log("stopped request");
            });
      console.log("finito get value");
   }
   //var canceler = $q.defer();
   //$scope.stopRequest = function ()
   //{
      //console.log("stop request");
      //canceler.resolve();
   //}
/*** Se si riesce a metterla quando si chiude la finestra ottimo, se no meglio togliere ***/
   //$scope.$on('$destroy', function ()
   //{
      //console.log("Destroying Istantaneo");
      //$scope.stopRequest();
      //console.log("Destroyed Istantaneo");
   //});
/******************************************************************************************/
   
   // PARAMETERS
   var widthMax = parseInt($window.innerWidth * 0.97);
   var potenzaMax = 4500;

   // INIT
   graficoIstantaneo(widthMax,potenzaMax);//$scope.potenza);
   getValue();
}]);




photoBerry.controller("graficoGiornalieroPotenzaController",
                        [  "$scope",
                           "$http",
                           "toStringForAJAX",
                           "lineGraph", 
                           "createDateFromTimeString",
               function ($scope,
                           $http,
                           toStringForAJAX,
                           lineGraph,
                           createDateFromTimeString
                           ) 
{
   // FROM FACTORIES
   var giorno;
   // FUNCTIONS
   request = function ()
   {  
      $http.get
         (
            "/potenzaGrafico",
            { 
               params: 
               {
                  giorno : toStringForAJAX(giorno),
               }
            }
         )
         .success( function (data)
            {
               $scope.dati = data["potenze"];
               for (i=0;i<$scope.dati.length;i++)
               {
                  $scope.dati[i].ora = createDateFromTimeString($scope.dati[i].ora,$scope.giorno);
               }
               lineGraph(selectionsObject,data["potenze"],d3.select('#lineGraphPotenza'),width,height);
               $scope.showGrafico = true;
            }
         ).error( function (data)
            {
               alert("ERRORE");
            }
         );
   }
   
   // PARAMETERS
   $scope.title = "Grafico Potenza";
   var today = new Date();
   $scope.maxDate = new Date(today.getFullYear(),today.getMonth(),today.getDate());
   $scope.giorno = $scope.maxDate;
   $scope.minDate = new Date(2014,11,8);//getMinDate; // mese parte con 0
   var width = 1200;
   var height = 650;
   var selectionsObject = 
      {
         svg : null,
         yAxisGroup : null,
         xAxisGroup : null,
         dataCirclesGroup : null,
         dataLinesGroup : null,
         title : null,
         yLabel : null,
         tip : null, // FUNCTION 
      };

   // INIT
   minDateRequest.success(function (data) 
      {
         $scope.minDate = new Date(Date.parse(data.dataMinima)); 
         $scope.minDate.setDate($scope.minDate.getDate() - 1);  // per qualche strano motivo, dipende dai settaggi del DatePicker
      }
   );
   
}]);








/*** MY FACTORY FUNCTIONS ***/
photoBerry.factory('minDateRequest', ['$http', function ($http)
   {
      return $http.get("/dataMinima")
   }
]);
/****************************/
/*** MY SERVICE FUNCTIONS ***/
photoBerry.factory('toStringForAJAX', function () 
   {
      var tmp = function (data) 
      {
         var year = (data.getFullYear()).toString();
         var month = data.getMonth() + 1;
         var day = data.getDate();
         if (month < 10)
         {
            month = "0"+month.toString();
         }
         else
         {
            month = month.toString();
         }
         if (day < 10)
         {
            day = "0"+day.toString();
         }
         else
         {
            day = day.toString();
         }
         return year+"-"+month+"-"+day;
      }
      return tmp;
   }
);

photoBerry.factory('anniMesiConstructor', function ()
   {
      var tmp = function (data, includiMeseInCorso) //data minima
      {
         var mesi = ["Gennaio","Febbraio","Marzo","Aprile","Maggio","Giugno","Luglio","Agosto","Settembre","Ottobre","Novembre","Dicembre"];
         var annoPrimoGiorno = Number(data.getFullYear()); 
         var mesePrimoGiorno = Number(data.getMonth());
         var dataOggi = new Date();
         var annoAdesso = Number(dataOggi.getFullYear());
         var meseAdesso = Number(dataOggi.getMonth());
         var annoTmp = annoPrimoGiorno;
         var mesiSelezionabili = [];
         var anniMesi = [];
         // ANNI
         //console.log("annoTmp: +" String(annoTmp));
         //console.log("annoAdesso: +" String(annoAdesso));

         while (annoTmp <= annoAdesso)
         {
            //console.log("While annoTmp: +" String(annoTmp));
            // MESI
            if (annoTmp == annoPrimoGiorno)
            {
               //console.log("annoTmp == annoPrimoGiorno");
               if (annoPrimoGiorno == annoAdesso)
               {
                  if (includiMeseInCorso)
                  {
                     for (i = mesePrimoGiorno; i <= meseAdesso; i++) // includo il mese in corso
                     {
                        mesiSelezionabili.push(mesi[i]);
                     }                  
                  }
                  else
                  {
                     for (i = mesePrimoGiorno; i < meseAdesso; i++) // il mese in corso non lo prendo
                     {
                        mesiSelezionabili.push(mesi[i]);
                     }
                  }
               }
               else
               {
                  for (i = mesePrimoGiorno; i < 12; i++) //fino a Dicembre
                  {
                     mesiSelezionabili.push(mesi[i]);
                  }
               }
            }
            else if (annoTmp == annoAdesso)
            {
               //console.log("annoTmp == annoAdesso");
               if (includiMeseInCorso)
               {
                  for (i = 0; i <= meseAdesso; i++) // includo il mese in corso
                  {
                     mesiSelezionabili.push(mesi[i]);
                  }                  
               }
               else
               {
                  for (i = 0; i < meseAdesso; i++) // il mese in corso non lo prendo
                  {
                     mesiSelezionabili.push(mesi[i]);
                  }
               }
            }
            else
            {
               console.log("annoTmp != annoPrimoGiorno && annoTmp != annoAdesso");
               // tutti i mesi
               mesiSelezionabili = mesi;  
            }
            
            if (mesiSelezionabili.length != 0) // !includiMeseInCorso && meseAdesso == 0)
            {
               // è falsa solo se siamo a gennaio e non includo il mese in corso, quindi non devo prendere questo anno
               anniMesi.push(
                  {
                     anno : annoTmp,
                     mesi : mesiSelezionabili
                  }
               );
            }

            annoTmp++;
            mesiSelezionabili = [];
         }
         return anniMesi;
      }
      return tmp;
   }
);
   
photoBerry.factory('capitalizeFirstLetter', function ()
   {
      var tmp = function (string)
      {
         return string.charAt(0).toUpperCase() + string.slice(1);
      }
      return tmp;
   }
);

photoBerry.factory('barGraph', ['capitalizeFirstLetter','nomiMesi', function (capitalizeFirstLetter,nomiMesi)
   {
      var tmp = function (giornateDelMese,campoPerAsseY,elementToAppendTo,svgWidth,svgHeight,margin,yAxisText,tooltipOffset,tooltipContent,yAxisLabelMargin)
      {
         // campoPerAsseY e' la stringa del campo dell'oggetto giornateDelMese da mostrare sull'asse y (o "potenza" o "produzione")
         var unitaMisura = { potenza: "W", produzione:"Wh" };
         if (typeof margin === 'undefined')              { margin = {top: 40, right: 20, bottom: 80, left: 70}; }
         if (typeof svgWidth === 'undefined')            { svgWidth = 960; }
         if (typeof svgHeight === 'undefined')           { svgHeight = 500; }
         if (typeof elementToAppendTo === 'undefined')   { elementToAppendTo = d3.select("body"); } //"body"; }
         if (typeof yAxisText === 'undefined')           { yAxisText = capitalizeFirstLetter(campoPerAsseY)+" ["+unitaMisura[campoPerAsseY]+"]"; }
         if (typeof tooltipOffset === 'undefined')       { tooltipOffset = -10; }
         if (typeof tooltipContent === 'undefined')      { tooltipContent = function (d) { return "<strong>"+capitalizeFirstLetter(campoPerAsseY)+":</strong> <span style='color:red'>" + d[campoPerAsseY] + " "+unitaMisura[campoPerAsseY]+"</span>" }; } 
         if (typeof yAxisLabelMargin === 'undefined')    { yAxisLabelMargin = 15; }
         
         var mese = nomiMesi(Number(giornateDelMese[0].giorno.slice(5,7)));
         var numeroGiorni = giornateDelMese.length;
         var width = svgWidth - margin.left - margin.right;
         var height = svgHeight - margin.top - margin.bottom;
         
         if (numeroGiorni >= 5 && numeroGiorni < 15)
            width = width / 2;
         else if (numeroGiorni < 5)
            width = width / 4;
         
         // .map() ritorna un array in cui ci sono gli elementi restituiti dalla funzione presa come parametro
         var x = d3.scale.ordinal()
            .domain(giornateDelMese.map(function (d) { return d.giorno }))
            .rangeRoundBands([0, width], .1);

         var y = d3.scale.linear()
            .domain([0,d3.max(giornateDelMese.map(function (d) { return d[campoPerAsseY] }))])
            .range([height, 0]);

         var xAxis = d3.svg.axis()
            .scale(x)
            .orient("bottom");

         var yAxis = d3.svg.axis()
            .scale(y)
            .orient("left")
            .tickFormat(function(d) { return d + " " + unitaMisura[campoPerAsseY]; });

         var tip = d3.tip()
            .attr('class', 'd3-tip')
            .offset([tooltipOffset, 0])
            .html(tooltipContent)

         var svg = elementToAppendTo.append("svg")
               .attr("width", width + margin.left + margin.right)
               .attr("height", height + margin.top + margin.bottom)
            .append("g")
               .attr("transform", "translate(" + margin.left + "," + margin.top + ")"); //questo e' il nuovo 0,0

         svg.call(tip); //COS'E' CALL???

         svg.append("g")
            .attr("class", "x axis")
            .attr("transform", "translate(" + yAxisLabelMargin + "," + height + ")") // yAxisLabelMargin sposta l'asse un po' a destra
            .call(xAxis)
               .selectAll("text")  
                  .style("text-anchor", "end")
                  .attr("dx", "-.8em")
                  .attr("dy", ".15em")
                  .attr("transform", "rotate(-35)");

         svg.append("g")
               .attr("class", "y axis")
               .call(yAxis)
            .append("text")
               .attr("class", "text")
               .attr("transform", "rotate(-90)")
               .attr("y", 6)
               .attr("dy", ".71em")
               .style("text-anchor", "end")
               .text(yAxisText);
               
         /* TITLE */
         svg.append("text")
            .attr("class","barGraphTitle")
            .attr("x", (width / 2))             
            .attr("y", 0 - (margin.top / 2))
            .attr("text-anchor", "middle")  
            .text(capitalizeFirstLetter(campoPerAsseY)+": "+mese);

         svg.selectAll(".bar")
               .data(giornateDelMese)
            .enter().append("rect")
               .attr("class", "bar")
               .attr("x", function(d) { return x(d.giorno) + yAxisLabelMargin; }) // yAxisLabelMargin sposta le barre un po' a destra
               .attr("width", x.rangeBand())
               .attr("y", function(d) { return y(d[campoPerAsseY]); })
               .attr("height", function(d) { return height - y(d[campoPerAsseY]); })
               .on('mouseover', tip.show)
               .on('mouseout', tip.hide)
              // .on('click', callback); // open quella giornata
         
         //function callback ()
         //{
            //alert("gigi");
         //}
      }
      
      return tmp;
   }
]);

photoBerry.factory('lineGraph', ['toStringForAJAX', function (toStringForAJAX)
   {
      var tmp = function (giaDisegnato,// = selectionsObject,
                           data,
                           elementToAppendTo,
                           w,// = width,
                           h,// = height,
                           maxDataPointsForDots,// = maxDataPointsForDotsLOC,
                           transitionDuration,// = transitionDurationLOC
                           margin,
                           yAxisLabelMargin,
                           yMax,
                           pointRadius,
                           min
                           ) 
      {
      /*** TO DO
      * BONUS
      *    ora inizio
      *    ora fine
      * 
      * 
      ***/  
         //var elementToAppendTo = d3.select('#lineGraphPotenza');
         //var data = $scope.dati;//generateData();
         if (typeof margin === 'undefined')   { margin = 40; }
         if (typeof yAxisLabelMargin === 'undefined') { yAxisLabelMargin = 30; }
         if (typeof yMax === 'undefined') { yMax = 3500; } // range massimo di y per la comparazione tra i diversi giorni
         if (typeof pointRadius === 'undefined') { pointRadius = 4; }
         if (typeof min === 'undefined') { min = 0; }
         if (typeof width === 'undefined') { width = 1200; }
         if (typeof height === 'undefined') { height = 650; }
         if (typeof maxDataPointsForDots === 'undefined') { maxDataPointsForDots = 300; }//50
         if (typeof transitionDuration === 'undefined') { transitionDuration = 500; }
         
         var marginLeft = margin + yAxisLabelMargin;
         var max = d3.max(data, function(d) { return d.potenza }) * 1.05; // se giornata finita metti sempre 4500
         var x = d3.time.scale().range([0, w - margin * 2]).domain([data[0].ora, data[data.length - 1].ora]);
         //var y = d3.scale.linear().range([h - margin * 2, 0]).domain([min, max]);
         
         var oggi = new Date();
         var dataDate = data[0].ora;
         if (dataDate.getFullYear() == oggi.getFullYear() 
               && dataDate.getMonth() == oggi.getMonth() 
               && dataDate.getDate() == oggi.getDate() )
         { // se è oggi
            var y = d3.scale.linear().range([h - margin * 2, 0]).domain([min, max]);
         }
         else
         {
            var y = d3.scale.linear().range([h - margin * 2, 0]).domain([min, yMax]);
         }
         
         var tooltipOffset = -10;
         var tooltipContent = function (d) { return "<strong>Potenza:</strong> <span style='color:red'>" + d['potenza'] + " W</span>" };
         /***************/
         
         var xAxis = d3.svg.axis().scale(x).tickSize(h - margin * 2).tickPadding(10).ticks(20)//.ticks(7)
         /***************/
            .tickFormat( function(d) { 
               var hours = d.getHours();
               var minutes = d.getMinutes();
               var hh,mm;
               if (hours < 10)
                  hh = "0"+String(hours);
               else
                  hh = String(hours);
               if (minutes < 10)
                  mm = "0"+String(minutes);
               else
                  mm = String(minutes);
               return hh+":"+mm; 
            })
            //.tickSize([ (data[0].ora), (data[data.length-1].ora) ]);
         /***************/
         ;
         
         var yAxis = d3.svg.axis().scale(y).orient('left').tickSize(-w + margin * 2).tickPadding(10)
         /**************/
            .tickFormat(d3.format(".0f"))
         /**************/
         ;
         var t = null;

         svg = elementToAppendTo.select('svg').select('g');
        // console.log(typeof svg);
         if (svg.empty()) {
            svg = elementToAppendTo//d3.select('#chart')
               .append('svg:svg')
                  .attr('width', w)
                  .attr('height', h)
                  .attr('class', 'viz')
               .append('svg:g')
                  .attr('transform', 'translate(' + marginLeft + ',' + margin + ')');
         }
         
         t = svg.transition().duration(transitionDuration);

      /***************/   
         // TITLE 
         if (!giaDisegnato)
         {
            title = svg.append("text")
               .attr("class","lineGraphTitle")
               .attr("x", (w / 2) - margin)             
               .attr("y", 0 - (margin / 2))
               .attr("text-anchor", "middle")
               .text("Potenza: " + toStringForAJAX(data[0].ora));
                    
            // y ticks and labels
            yAxisGroup = svg.append('svg:g')
               .attr('class', 'yTick')
               .call(yAxis);   
            // y label
            yLabel = svg.append("text")
               .attr("class", "yAxisText")
               .attr("transform", "rotate(-90)")
               .attr("y", -65) // based on yAxisTicks
               .attr("x", -(h/2) + margin*1.5) // * 1.5 per scentrarlo verso su
               .attr("dy", ".71em")
               .style("text-anchor", "middle") //"end")
               .text("Potenza [W]");   
            // x ticks and labels
            xAxisGroup = svg.append('svg:g')
               .attr('class', 'xTick')
               .call(xAxis);   
            // Draw the lines  
            dataLinesGroup = svg.append('svg:g');
            // Draw the points
            dataCirclesGroup = svg.append('svg:g');
            // tip
            tip = d3.tip()
               .attr('class', 'd3-tip')
               .offset([tooltipOffset, 0])
               .html(tooltipContent)
            svg.call(tip);

         }
         else
         {
            t.select('.lineGraphTitle').text("Potenza: " + toStringForAJAX(data[0].ora));
            // y ticks and labels
            t.select('.yTick').call(yAxis);  
            // x ticks and labels
            t.select('.xTick').call(xAxis);
         }

         var dataLines = dataLinesGroup.selectAll('.data-line')
               .data([data]);

         var line = d3.svg.line()
            // assign the X function to plot our line as we wish
            .x(function(d,i) { 
               // verbose logging to show what's actually being done
               //console.log('Plotting X value for date: ' + d.date + ' using index: ' + i + ' to be at: ' + x(d.date) + ' using our xScale.');
               // return the X coordinate where we want to plot this datapoint
               //return x(i); 
               return x(d.ora); 
            })
            .y(function(d) { 
               // verbose logging to show what's actually being done
               //console.log('Plotting Y value for data value: ' + d.value + ' to be at: ' + y(d.value) + " using our yScale.");
               // return the Y coordinate where we want to plot this datapoint
               //return y(d); 
               return y(d.potenza); 
            })
            .interpolate("linear");

             /*
             .attr("d", d3.svg.line()
             .x(function(d) { return x(d.date); })
             .y(function(d) { return y(0); }))
             .transition()
             .delay(transitionDuration / 2)
             .duration(transitionDuration)
               .style('opacity', 1)
                              .attr("transform", function(d) { return "translate(" + x(d.date) + "," + y(d.value) + ")"; });
              */

         var garea = d3.svg.area()
            .interpolate("linear")
            .x(function(d) { 
               // verbose logging to show what's actually being done
               return x(d.ora); 
            })
                     .y0(h - margin * 2)
            .y1(function(d) { 
               // verbose logging to show what's actually being done
               return y(d.potenza); 
            });

         dataLines
            .enter()
            .append('svg:path')
                     .attr("class", "area")
                     .attr("d", garea(data));

         dataLines.enter().append('path')
             .attr('class', 'data-line')
             .style('opacity', 0.3)
             .attr("d", line(data));
            /*
            .transition()
            .delay(transitionDuration / 2)
            .duration(transitionDuration)
               .style('opacity', 1)
               .attr('x1', function(d, i) { return (i > 0) ? xScale(data[i - 1].date) : xScale(d.date); })
               .attr('y1', function(d, i) { return (i > 0) ? yScale(data[i - 1].value) : yScale(d.value); })
               .attr('x2', function(d) { return xScale(d.date); })
               .attr('y2', function(d) { return yScale(d.value); });
            */

         dataLines.transition()
            .attr("d", line)
            .duration(transitionDuration)
               .style('opacity', 1)
                              .attr("transform", function(d) { return "translate(" + x(d.ora) + "," + y(d.potenza) + ")"; });

         dataLines.exit()
            .transition()
            .attr("d", line)
            .duration(transitionDuration)
                              .attr("transform", function(d) { return "translate(" + x(d.ora) + "," + y(0) + ")"; })
               .style('opacity', 1e-6)
               .remove();

         d3.selectAll(".area").transition()
            .duration(transitionDuration)
            .attr("d", garea(data));

         var circles = dataCirclesGroup.selectAll('.data-point')
            .data(data);

         circles
            .enter()
               .append('svg:circle')
                  .attr('class', 'data-point')
                  .style('opacity', 1e-6)
                  .attr('cx', function(d) { return x(d.ora) })
                  .attr('cy', function() { return y(0) })
                  .attr('r', function() { return (data.length <= maxDataPointsForDots) ? pointRadius : 0 })
      .on('mouseover', tip.show)
      .on('mouseout', tip.hide)
               .transition()
               .duration(transitionDuration)
                  .style('opacity', 1)
                  .attr('cx', function(d) { return x(d.ora) })
                  .attr('cy', function(d) { return y(d.potenza) });

         circles
            .transition()
            .duration(transitionDuration)
               .attr('cx', function(d) { return x(d.ora) })
               .attr('cy', function(d) { return y(d.potenza) })
               .attr('r', function() { return (data.length <= maxDataPointsForDots) ? pointRadius : 0 })
               .style('opacity', 1);

         circles
            .exit()
               .transition()
               .duration(transitionDuration)
                  // Leave the cx transition off. Allowing the points to fall where they lie is best.
                  //.attr('cx', function(d, i) { return xScale(i) })
                  .attr('cy', function() { return y(0) })
                  .style("opacity", 1e-6)
                  .remove();    
      }
      return tmp;
   }
]);

photoBerry.factory('graficoIstantaneo', ['redrawGraph', function (redrawGraph)
   {
      var tmp = function (widthMax,potenzaMax,potenza)
      {
         if (typeof potenza === 'undefined')
         {
            //console.log("potenza undefined")
            potenza = 0;
         }
         /*width = potenza / potenzaMax * widthMax;
         var widthLabel;
         if (potenza >= 189)
            widthLabel = var carName = "BMW";width;
         else if (potenza < 100 && potenza >= 10)
            widthLabel = 150 / potenzaMax * widthMax;
         else if (potenza < 10)
            widthLabel = 130 / potenzaMax * widthMax;
         else
            widthLabel = 190 / potenzaMax * widthMax;*/
         d3.select(".graficoIstantaneo")
            .append("div")
               .attr("class","istantaneoLabel")
               //.style("width", String(widthLabel) + "px" )
               .html(String(potenza)+" <b>W</b>");
         d3.select(".graficoIstantaneo")
            .append("div")
               .attr("class","istantaneoBarraContorno")
               .style("width",String(widthMax) + "px"); // 3 borderWidth +3*2)
         d3.select(".istantaneoBarraContorno")
            .append("div")
               .attr("class","istantaneoBarra")
               //.style("width", String(width) + "px" );
         d3.select(".graficoIstantaneo")
            .append("div")
               .attr("class","istantaneoBarraContornoLabel")
               .style("width",String(widthMax) + "px")
               .html(String(potenzaMax)+" <b>W</b>");
         redrawGraph(potenza,widthMax,potenzaMax);
      }
      return tmp;      
   }
]);

photoBerry.factory("redrawGraph", function () 
{
   var tmp = function (potenza,maxWidth,maxPotenza)
   {
      if (potenza == -1)
      {
         d3.select(".istantaneoLabel")
            .style("width", "140px" )
            .html("Impianto Spento");
         d3.select(".istantaneoBarra")
            .style("width", "0px" );
      }
      else if (potenza == 0)
      {
         d3.select(".istantaneoLabel")
            .style("width", "130px" )
            .html("Waiting for data");
         d3.select(".istantaneoBarra")
            .style("width", "0px" );
      }
      else
      {
         var width = potenza / maxPotenza * maxWidth;
         var widthLabel;
         if (potenza >= 189)
            widthLabel = width;
         else if (potenza < 100 && potenza >= 10)
            widthLabel = 160 / maxPotenza * maxWidth;
         else if (potenza < 10)
            widthLabel = 130 / maxPotenza * maxWidth;
         else
            widthLabel = 190 / maxPotenza * maxWidth; // 190 scelto in base al font del label
         d3.select(".istantaneoLabel")
            .style("width", String(widthLabel) + "px" )
            .html(String(potenza)+" <b>W</b>");
         d3.select(".istantaneoBarra")
            .style("width", String(width) + "px" );
      }
   }
   return tmp;
});

photoBerry.factory("createDateFromTimeString", function ()
{
   var tmp = function (timeString,giorno) // giorno is a date object
   {
      // From 08:07:55 create date with that time; giorno provides the year, month and day
      var date = new Date(giorno);
      var i = 0;
      var hour = 0;
      var minute = 0; 
      var second = 0;
      while (timeString[i] != ':')
      {
         hour = ( hour*10 + Number(timeString[i]) );
         i++;
      }
      i++;
      while (timeString[i] != ':')
      {
         minute = ( minute*10 + Number(timeString[i]) );
         i++;
      }
      i++;
      while (i < timeString.length)
      {
         second = ( second*10 + Number(timeString[i]) );
         i++;
      }
      date.setHours(hour, minute, second, 0);
      return date;
   }
   return tmp;
});

photoBerry.factory("numeriMesi", function ()
   {
      var tmp = function (meseString)
      {
         switch (meseString) {
            case "Gennaio":
               return 1;
            case "Febbraio":
               return 2;
            case "Marzo":
               return 3;
            case "Aprile":
               return 4;
            case "Maggio":
               return 5;
            case "Giugno":
               return 6;
            case "Luglio":
               return 7;
            case "Agosto":
               return 8;
            case "Settembre":
               return 9;
            case "Ottobre":
               return 10;
            case "Novembre":
               return 11;
            case "Dicembre":
               return 12;
            default:
               return "ERRORE";
         } 
      }
      return tmp;
   }
);

photoBerry.factory("nomiMesi", function ()
   {
      var tmp = function (numeroMese)
      {
         switch (numeroMese) {
            case 1:
               return "Gennaio";
            case 2:
               return "Febbraio";
            case 3:
               return "Marzo";
            case 4:
               return "Aprile";
            case 5:
               return "Maggio";
            case 6:
               return "Giugno";
            case 7:
               return "Luglio";
            case 8:
               return "Agosto";
            case 9:
               return "Settembre";
            case 10:
               return "Ottobre";
            case 11:
               return "Novembre";
            case 12:
               return "Dicembre";
            default:
               return "ERRORE";
         } 
      }
      return tmp;
   }
);
/********************/
