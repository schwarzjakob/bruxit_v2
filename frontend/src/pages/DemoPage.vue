<template>
<el-row>
    <el-button type="primary"> <el-icon> <ArrowLeft /> </el-icon> Sleep Stage Detection</el-button>
    <el-tag type="success">Advanced</el-tag>
    <PipelineStepper :step="3"/>
    <el-button type="primary"> Monitoring Dashboards  <el-icon> <ArrowRight /> </el-icon></el-button>
    
</el-row>


</template>

<script>
import { ArrowLeft, ArrowRight} from '@element-plus/icons-vue'
import PipelineStepper from '../components/PipelineStepper.vue'

export default {
    name: 'DemoPage',
    data () {
        return{

        }
    },
    components: {
        ArrowLeft,
        ArrowRight,
        PipelineStepper
    },
    methods: {

    }
}
</script>