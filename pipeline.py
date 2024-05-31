from subtoaudiomod import SubToAudio

#best speakers :
#'Viktor Eka'
#'Luis Moray'
#'Torcull Diarmuid'
_speaker = 'Torcull Diarmuid'
models = SubToAudio().coqui_model()
sub = SubToAudio(model_name=models[0], progress_bar=True)


subtitle = sub.subtitle("srt/lecture-1.2-captions.mod.srt")
print("--------------->>>>>>>> Subtitle has ["+str(len(subtitle))+"] lines...")
sub.convert_to_audio(sub_data=subtitle, speaker=_speaker, output_path="./audio/lecture-1.2-captions_Torcull")
