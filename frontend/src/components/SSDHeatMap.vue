<template>
    <el-row style="margin-bottom: -20px;">
        <el-col :offset="18">
            <el-button @click="editSelected"><p v-if="isEditMode">Save</p><p v-else>Edit</p></el-button>
        </el-col>
    </el-row>
    <el-row v-loading="!ssdDataReceived" :element-loading-text="this.getLoadingTime()" justify="center">
        <div id="ssd" style="width: 1500px; height: 800px;"></div>
    </el-row>

</template>

<script>
import * as echarts from 'echarts';
import { markRaw } from 'vue';
import axios from 'axios';
import { ElMessage } from 'element-plus'


export default{
    name: 'SSDHeatMap',
    data () {
        return {
            ssdData: [],
            ssdDataReceived: false,
            loadingSPerGb: 20, 
            isEditMode: false,
            ssdChart: null,
            options: {},
            selected: []
        }
    },
    async mounted(){
        await this.getSsdData();
        await this.drawSSDHeatMap();
    },
    methods: {
        getLoadingTime(){
            let loadingTimeS = parseInt(this.$store.state.fileSize * this.loadingSPerGb);

            let minutes = parseInt(loadingTimeS / 60);

            let seconds = parseInt(loadingTimeS - (60*minutes))



            if(minutes >= 1){
                return "The dataset is loading...it will take around " + minutes + " minute and " + seconds + " seconds."
            } else {
                return "The dataset is loading...it will take around " + seconds + " seconds."
            }
        },
        async getSsdData(){
            const path = `http://127.0.0.1:5000/ssd/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`
            const headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
            };

            await axios.get(path, {headers})
                .then((res) => {
                    console.log(res.data)
                    this.ssdData = res.data;
                    this.ssdDataReceived = true;

                })
                .catch(err=>{
                    console.log(err)
                })
    
        },
        isRem(entry){
            if(entry['stage'] === 'rem'){
                return entry['stage']
            }
        },
        isNrem(entry){
            if(entry['stage'] === 'nrem'){
                return entry['stage']
            }
        },
        isSelected(entry){
            if(entry['selected']){
                return entry['selected']
            }
        },
        getMax(arr, prop) {
            var max = 0;
            for (var i=0 ; i<arr.length ; i++) {
                if (parseInt(arr[i][prop]) > parseInt(max))
                    max = arr[i][prop];
            }
            return max;
        },
        editSelected(){
            console.log("ready to edit")
            this.isEditMode = !this.isEditMode;

            if(this.isEditMode == true){
                ElMessage('Please select or deselect the intervals that you want to include in the events classification step.')
            }

            if(this.isEditMode == false){
                ElMessage({message: 'Updated selected intervals.', type: 'success'})
                console.log("SAVE AND UPDATE TO DB")

                const path = `http://127.0.0.1:5000/selected-intervals/${this.$store.state.patientId}/${this.$store.state.weekId}/${this.$store.state.file}`
                const headers = {
                        'Accept': 'application/json',
                        'Content-Type': 'application/json'
                };

                let payload = [];

                for(let i=0; i<this.selectedData.length; i++){
                    payload.push({
                        "x": this.selectedData[i][0],
                        "y": this.selectedData[i][1],
                    })
                }

                console.log("PAYLOAD: ", payload)
                
                axios.post(path, payload, {headers})
                    .then((res) => {
                        console.log(res.data)
                        console.log("posted selected intervals.")
                    })
                    .catch(err=>{
                        console.log(err)
                    })

            }
        },
        async drawSSDHeatMap(){

            let chartInstance = markRaw(echarts.init(document.getElementById('ssd')));
            let option;

            const minutes = [
                5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 80, 85, 90
            ];            

            let maxY = this.getMax(this.ssdData, 'y');

            console.log(maxY)

            const sleepCycles = Array.from({length: maxY+1}, (_, i) => i + 1);

            console.log("sleep cycles: ", sleepCycles)

            let remData = this.ssdData.filter(this.isRem);
            let nremData = this.ssdData.filter(this.isNrem);
            this.selectedData = this.ssdData.filter(this.isSelected)

            console.log(this.selectedData)

            remData = remData
                .map(function (item) {
                return [item['x'], item['y'], Math.round(item['HRV_SDNN']), item['stage'],  item['HRV_LFHF']];
            });



            nremData = nremData
                .map(function (item) {
                return [item['x'], item['y'], Math.round(item['HRV_SDNN']), item['stage'],  item['HRV_LFHF']];
            });

            this.selectedData = this.selectedData
                .map(function (item) {
                return [item['x'], item['y'], Math.round(item['HRV_SDNN']), item['stage'],  item['HRV_LFHF']];
            });
            console.log("Selected: ", this.selectedData)

            option = {
                tooltip: {
                    position: 'top',
                    formatter: function (params) {
                        return `${params.value[3]}<br />
                                ${params.marker}: ${params.value[4].toFixed(2)} ± ${params.value[2]}`;
                    }
                },
                grid: {
                    height: '50%',
                    top: '10%'
                },
                xAxis: {
                    type: 'category',
                    data: minutes,
                    splitArea: {
                        show: true
                    }
                },
                yAxis: {
                    type: 'category',
                    data: sleepCycles,
                    inverse: true,
                    show: true,
                    splitArea: {
                        show: true
                    }
                },
                visualMap: [
                {
                    type: 'continuous',
                    dimension: 2,
                    seriesIndex: 1,
                    min: Math.min(...remData.map(item => item[2])), // Min value of HRV_SDNN for NREM
                    max: Math.max(...remData.map(item => item[2])), // Max value of HRV_SDNN for NREM
                    inRange: {
                        color: ['#808080', '#E0E0E0'] // Grey scale for NREM
                    },
                    text: ["high uncertainty (high SD)", "low uncertainity (low SD)"],
                    outOfRange: {
                        color: 'transparent'
                    },
                    controller: {
                        inRange: { color: ['#808080', '#E0E0E0'] }
                    },
                    calculable: false,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '24%',
                },
                {
                    type: 'continuous',
                    dimension: 2,
                    seriesIndex: 0,
                    min: Math.min(...nremData.map(item => item[2])), // HRV_SDNN for REM
                    max: Math.max(...nremData.map(item => item[2])),
                    inRange: {
                        color: ['#0050B3', '#D1E9FF'] // Blue scale for REM
                    },
                    outOfRange: {
                        color: 'transparent'
                    },
                    controller: {
                        inRange: { color: ['#0050B3', '#D1E9FF'] }
                    },
                    text: ["high uncertainty (high SD)", "low uncertainity (low SD)"],
                    calculable: false,
                    orient: 'horizontal',
                    left: 'center',
                    bottom: '30%',
                },
                {
                    dimension: 2,
                    seriesIndex : 2,
                    calculable: false,
                    show: false,
                    inRange: {
                        color: []
                    }
                }
                ],
                series: [
                    {
                    name: 'REM data',
                    type: 'heatmap',
                    data: remData,
                    seriesIndex: 0,
                    label: {
                        show: true,
                        formatter: function () {
                            return 'REM';
                        },
                        color: '#FFFFFF'
                    },
                    emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                    }
                    },
                    {
                    name: 'NREM data',
                    type: 'heatmap',
                    data: nremData,
                    seriesIndex: 1,
                    label: {
                        show: true,
                        formatter: function () {
                            return '';
                        },
                        color: '#FFFFFF'
                    },
                    emphasis: {
                            itemStyle: {
                                shadowBlur: 10,
                                shadowColor: 'rgba(0, 0, 0, 0.5)'
                            }
                    }
                    }, 
                    {
                        type: 'heatmap',
                        data: this.selectedData,
                        seriesIndex: 2,
                        label: {
                            show: false
                        },
                        itemStyle: {
                            borderColor: 'black',
                            borderType: 'solid',
                            borderWidth: 2
                        }
                    }
                ]
            };
            chartInstance.setOption(option);

            // Add a click event listener
            chartInstance.on('click', function(params) {
                // Extract the coordinates of the clicked tile
                var x = params.value[0];
                var y = params.value[1];
                var sdnn = params.value[2];
                var stage = params.value[3];
                var lfhf = params.value[4];
                
                console.log(this.isEditMode)

                if(this.isEditMode === true){
                    console.log("x: ", x)
                    console.log("y: ", y)
                    console.log("sdnn: ", sdnn)
                    console.log("stage: ", stage)
                    console.log("lfhf: ", lfhf)

                    var entry = [x, y, sdnn, stage, lfhf]
                    console.log(entry)
                    console.log(this.selectedData)

                    if(JSON.stringify(this.selectedData).includes(JSON.stringify(entry))){
                        console.log("included")
                        this.selectedData = this.selectedData.filter(function(el) { return JSON.stringify(el) != JSON.stringify(entry); });
                        console.log(this.selectedData)
                        option.series[2].data = this.selectedData;
                        chartInstance.setOption(option);

                    } else {
                        console.log("not included")
                        this.selectedData.push(entry)
                        option.series[2].data = this.selectedData;
                        chartInstance.setOption(option);
                    }
                }
            }.bind(this));


        }
    }
}
</script>