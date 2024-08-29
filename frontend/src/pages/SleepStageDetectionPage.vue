<template>
<h1>Sleep stage Detection Page</h1>

Patient {{ this.$store.state.patientId }}, Week {{ this.$store.state.weekId }}, file {{ this.$store.state.file }}, size {{ this.$store.state.fileSize }} GB
</template>

<script>
export default{
    name: 'SleepStageDetection',
    mounted(){
        console.log(this.$store.state.patientId)
        console.log(this.$store.state.weekId)
        console.log(this.$store.state.file)
        console.log(this.$store.state.fileSize)
    }
}
</script>