// Initialize the Amazon Cognito credentials provider
AWS.config.region = 'us-east-2'; // Region
AWS.config.credentials = new AWS.CognitoIdentityCredentials({
    IdentityPoolId: 'us-east-2:81f8a4e5-1143-4b24-9e7a-659a7105dc3d',
});

console.log('Connecting to AWS')
// Initialize the Cognito Sync client
AWS.config.credentials.get(function(){

    var syncClient = new AWS.CognitoSyncManager();
        
    syncClient.openOrCreateDataset('myDataset', function(err, dataset) {
        dataset.put('myKey', 'myValue', function(err, record){
            dataset.synchronize({
                onSuccess: function(data, newRecords) {
                    console.log('Connected!')
                }
            });
        });
    });
});   

console.log('Try dynamodb connection')
var dynamodb = new AWS.DynamoDB({apiVersion: '2012-08-10'});

//Generating a string of the last X hours back
var ts = new Date().getTime(); 
var tsOld = (ts - (14*24 * 3600) * 1000); // 14 days * 24 hours per day
var d = new Date(tsOld);
 
//Forming the DynamoDB Query
var params = {
	TableName: 'mc-test',                
	Limit: 2500,
	ConsistentRead: false,
	ScanIndexForward: true,
	ExpressionAttributeValues:{
		":clientId": "MC-1126-1-1",
        ":start_date": tsOld.toString()
	},
    KeyConditionExpression:
    	"clientId = :clientId AND ts >= :start_date"
}

//Query DynamoDB using the new documentClient
var docClient = new AWS.DynamoDB.DocumentClient();
docClient.query(params, function(err, data) {
    if (err) console.log(err, err.stack); // an error occurred
    else{
        var temp = [];
        var light = [];
        var rh = [];
        var moisture = [];
        var pump = [];
        var ts = 0;
        
        data.Items.forEach(function(item) {
            ts = item.ts * 1000; // sec to ms
            ts = ts - (4 * 60 * 60 * 1000); // time zone correction: -5 hours to ms
            temp.push([ts, item.payload.temp]);
            light.push([ts, item.payload.light]);
            rh.push([ts, item.payload.rh]);
            moisture.push([ts, item.payload.moisture]);
            pump.push([ts, item.payload.pump]);
        });

        Highcharts.chart('container', {
            title: {
                text: 'MC3.0'
            },
            chart: {
                zoomType: 'x'
            },
            legend: {
                layout: 'vertical',
                align: 'right',
                verticalAlign: 'middle'
            },
            xAxis: {
                type: 'datetime', // The types are 'linear', 'logarithmic' and 'datetime'
            },
            series: [{
                name: 'Temp',
                data: temp
                },{
                name: 'Light',
                data: light
                },{
                name: 'Relative Humidity',
                data: rh
                },{
                name: 'Moisture',
                data: moisture
                },{
                name: 'Pump',
                data: pump
            }],
        });
    }
});