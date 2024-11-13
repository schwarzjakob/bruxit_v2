<template>
<el-card>
    <template #header>
        <div class="card-header">
            <span><b>Legend</b></span>
            <p>Every row represents a sleep cycle of 90 minutes (1.5 hour)</p>

            <el-button @click="dialogTableVisible = true">
                Values from Ako et al. paper
            </el-button>

            <el-dialog v-model="dialogTableVisible" style="text-align:center; max-width: 600px">
                <template #header="{ titleId, titleClass }">
                <div class="my-header">
                    <h4 :id="titleId" :class="titleClass">Ako et al. (2003) - Median and interquartile range of HRV LF/HF ratio in REM vs. NREM.</h4>
                </div>
                </template>
                <el-table :data="gridData">
                <el-table-column fixed property="index" label="" width="150"/>
                <el-table-column property="REM" label="REM Median (IQR)" width="200" />
                <el-table-column property="NREM" label="NREM Median (IQR)" />
                </el-table>
            </el-dialog>
        </div>
    </template>
    <el-row>
        <div class="rem-box" style="margin-top: 3%; display: inline-block; margin-right: 4%; color:white; text-align: center; vertical-align: middle;">REM</div><div style="margin-top: 25px">REM interval (5 min)</div>
    </el-row>
    <el-row>
        <div class="nrem-box" style="margin-top: 3%; display: inline-block; margin-right: 4%; vertical-align: middle;" /><div style="margin-top: 25px">NREM interval (5 min)</div>
    </el-row>
    <el-row>
        <div class="rem-visualmap" style="margin-top: 3%; display: inline-block; margin-right: 4%; color:white; text-align: center; vertical-align: middle;" /><div style="margin-top: 16px">REM intervals uncertainity (SD)</div> <el-tooltip placement="top" effect="light">
    <template #content>The level of uncertainity is derived from the Standard deviation of the LF/HF measure of the Heart Rate Variability (HRV) analyis. <br /> The ranges to classify the different sleep stages were taken from the following study: <br /><a href="https://www.frontiersin.org/articles/10.3389/fphys.2017.01100/full">Herzig, David, et al. "Reproducibility of heart rate variability is parameter and sleep stage dependent." Frontiers in physiology 8 (2018): 1100.</a> </template>
        <el-button size="small" circle ><el-icon><InfoFilled /></el-icon></el-button>
    </el-tooltip>
        </el-row>
        <el-row>
            <div class="nrem-visualmap" style="margin-top: 3%; display: inline-block; margin-right: 4%; color:white; text-align: center; vertical-align: middle;" /><div style="margin-top: 16px">NREM intervals uncertainity (SD)</div> <el-tooltip placement="top" effect="light">
    <template #content>The level of uncertainity is derived from the Standard deviation of the LF/HF measure of the Heart Rate Variability (HRV) analyis. <br /> The ranges to classify the different sleep stages were taken from the following study: <br /><a href="https://www.frontiersin.org/articles/10.3389/fphys.2017.01100/full">Herzig, David, et al. "Reproducibility of heart rate variability is parameter and sleep stage dependent." Frontiers in physiology 8 (2018): 1100.</a> </template>
    <el-button size="small" circle ><el-icon><InfoFilled /></el-icon></el-button>
    </el-tooltip>
        </el-row>
        <el-row><div class="box" style="margin-top: 3%; display: inline-block; margin-right: 4%; vertical-align: middle;"/><div style="margin-top: 25px">Selected interval</div></el-row>
    </el-card> 
</template>

<script>
import { ref } from 'vue';
export default {
    name: 'SleepHeatMapLegend',
    data(){
        return{
            dialogTableVisible: ref(false),
            gridData: [{
                index: 'LF/HF ratio',
                REM: '2.51 (2.34, 2.68)',
                NREM: '0.935 (0.72, 2.59)'
            }]
        }
    }
}
</script>


<style>
.box {
    width:50px;
    height:40px;
    border-style: solid; border-width:3px;
    position: relative; 
}

.rem-box {
    width:50px;
    height:40px;
    background-color: #0050B3;
    position: relative; 
    line-height: 40px;
}

.nrem-box {
    width:50px;
    height:40px;
    background-color: #808080;
    position: relative;
}

.rem-visualmap {
    border-radius: 6px;
    background-image: linear-gradient(to right, #0050B3, #D1E9FF);
    width: 60px;
    height: 20px;
}

.nrem-visualmap {
    border-radius: 6px;
    background-image: linear-gradient(to right, #808080, #E0E0E0);
    width: 60px;
    height: 20px;
}
</style>