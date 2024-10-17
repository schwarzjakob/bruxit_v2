<template>
    <el-steps :active="step">
        <el-step title="Patients Data"  />
        <el-step title="Events Classification"  />
        <el-step title="Monitoring Dashboards" />
  </el-steps>
</template>
  

<script>
    export default {
        name: "PipelineStepper",
        props: ['step'],
        inheritAttrs: false,

    }
</script>
