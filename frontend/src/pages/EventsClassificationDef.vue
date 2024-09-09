<template>
    <!--HEADER ROW-->
    <el-row style="margin-top: 10px;">
        <el-col :span="2"><router-link :to="'/ssd/'"><el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Sleep Stage Detection</el-button></router-link></el-col>
        <el-col :span="1" :offset="2"><el-tag type="success" size="large">Advanced</el-tag></el-col>
        <el-col :span="13" :offset="1"><PipelineStepper :step="2" /></el-col>
        <el-col :span="2" :offset="1"><el-button type="primary"> Monitoring Dashboards  <el-icon> <ArrowRight /> </el-icon></el-button></el-col>
    </el-row>
    <el-row justify="center">
        <h1>Events Classification</h1>
    </el-row>

    <!--IMAGE ROW-->
    <el-row justify="center"> <h3>Patient {{ this.$store.state.patientId }}, Week {{ this.$store.state.weekId }}, file {{ this.$store.state.file }}, size {{ this.$store.state.fileSize }} GB</h3></el-row>

    <el-row justify="center">
        <h3>Signal and predicted events</h3>
        <el-button type="info" @click="toggleImage" style="margin-left: 20px; margin-top: 10px" plain>
        {{ isImageVisible ? 'Hide' : 'Show' }} Image
        </el-button>    
    </el-row>
    <el-row justify="center">
        <el-image v-if="isImageVisible" :src="nightPredImg" style="max-width: 900px" :preview-src-list="[nightPredImg]" fit="cover"/>
    </el-row>
</template>

<script>
//import { ref } from 'vue'
//import * as echarts from 'echarts';
//import csv from '../assets/1022102cFnorm_rms_5_min_256Hz.csv'; // Adjust the path as needed
//import { PriceTag, Refresh, InfoFilled } from '@element-plus/icons-vue'
//import img from '../../../backend/src/data/p1_wk1/1022102.png'
import img from '../assets/NightOverview.png'
//import { reactive } from 'vue'
import PipelineStepper from '../components/PipelineStepper.vue'

export default{
    name: 'EventsClassificationDef',
    components: {
        PipelineStepper
    },
    data () {
        return {
            isImageVisible: true,
            nightPredImg: img,
        }
    },
    methods: {
        toggleImage() {
            this.isImageVisible = !this.isImageVisible;
        },
    }
    
}
</script>