<template>
    <el-row style="margin-top: 10px;">
    <el-col :span="2"><router-link :to="'/ec-def/'"><el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Sleep Stage Detection</el-button></router-link></el-col>
        <el-col :span="1" :offset="2"><el-tag type="success" size="large">Advanced</el-tag></el-col>
        <el-col :span="13" :offset="1"><PipelineStepper :step="2" /></el-col>
    </el-row>
<h1>Monitoring</h1>

</template>

<script>
import PipelineStepper from '../components/PipelineStepper.vue'

export default {
    name: "MonitoringPage",
    components: {
        PipelineStepper
    }
}
</script>