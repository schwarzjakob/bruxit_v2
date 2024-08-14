<template>
    <el-steps :active=step finish-status="process" align-center>
        <el-step :title="'Patients Data'" description="Select the desired patient" :icon="User" />
        <el-step title="Filtering" description="Filter out undesired intervals" :icon="Filter" />
        <el-step title="Events Classification" description="Label events in the data" :icon="Open" />
        <el-step title="Treatment Analysis" description="Compare data between different days and weeks" :icon="DataLine" />
    </el-steps>
</template>

<script>
    export default {
        name: "PipelineStepper",
        props: ['step'],
        inheritAttrs: false,
    }
</script>

<script setup>
import { User, Filter, Open, DataLine } from '@element-plus/icons-vue'
</script>
