<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import { warpathAudio } from '$lib/game/audio';
  import { eventEmitter } from '$lib/game/eventEmitter';

  let unsubscribe = () => {};

  onMount(() => {
    unsubscribe = eventEmitter.subscribeOnMount({
      audioUnlock: () => {
        void warpathAudio.unlock();
      },
      audioMuteSet: (event) => {
        warpathAudio.setMuted(event.muted);
      },
      reelsSpin: (event) => {
        warpathAudio.playSpin(event.mode);
      },
      cascadeExplode: (event) => {
        warpathAudio.playCascade(event.step);
      },
      wildPulse: () => {
        warpathAudio.playWild();
      },
      globalMultiplier: () => {
        warpathAudio.playMultiplier();
      },
      featureIntro: () => {
        warpathAudio.playFeatureIntro();
      },
      winCounter: (event) => {
        warpathAudio.playWin(event.amount, event.level);
      },
      finalWin: (event) => {
        warpathAudio.playFinalWin(event.amount);
      }
    });
  });

  onDestroy(() => {
    unsubscribe();
  });
</script>
