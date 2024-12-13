FROM ubuntu:20.04

EXPOSE 5001

WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && \
    apt-get install -y -qq ffmpeg aria2 && apt clean && \
    apt-get install -y software-properties-common && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN add-apt-repository ppa:deadsnakes/ppa

RUN apt-get update && \
    apt-get install -y build-essential python-dev python3-dev python3.9-distutils python3.9-dev python3.9 curl && \
    apt-get clean && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.9 1 && \
    curl https://bootstrap.pypa.io/get-pip.py | python3.9

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.9 1

COPY . .

RUN python3 -m pip install --upgrade pip==24.0

RUN python3 -m pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

RUN python3 -m pip install --no-cache-dir -r requirements.txt
RUN python3 -m pip install mega.py gdown==5.1.0 pytube pydub gradio==3.42.0
RUN python3 -m pip install --no-cache-dir redis==5.2.1

RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/D40k.pth -d assets/pretrained_v2/ -o D40k.pth
RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/G40k.pth -d assets/pretrained_v2/ -o G40k.pth
RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0D40k.pth -d assets/pretrained_v2/ -o f0D40k.pth
RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/pretrained_v2/f0G40k.pth -d assets/pretrained_v2/ -o f0G40k.pth

RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/uvr5_weights/HP2-人声vocals+非人声instrumentals.pth -d assets/uvr5_weights/ -o HP2-人声vocals+非人声instrumentals.pth
RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/uvr5_weights/HP5-主旋律人声vocals+其他instrumentals.pth -d assets/uvr5_weights/ -o HP5-主旋律人声vocals+其他instrumentals.pth

RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/hubert_base.pt -d assets/hubert -o hubert_base.pt

RUN aria2c --console-log-level=error -c -x 16 -s 16 -k 1M https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe.pt -d assets/rmvpe -o rmvpe.pt

ENV OPENBLAS_NUM_THREADS=1 \
    no_proxy=localhost,127.0.0.1,::1 \
    weight_root=assets/weights \
    weight_uvr5_root=assets/uvr5_weights \
    index_root=logs \
    outside_index_root=assets/indices \
    rmvpe_root=assets/rmvpe \
    audio_temp_root=app/temp \
    request_channel=voice_change_request \
    response_channel=voice_change_response

ENV sha256_hubert_base_pt=f54b40fd2802423a5643779c4861af1e9ee9c1564dc9d32f54f20b5ffba7db96 \
    sha256_rmvpe_pt=6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193 \
    sha256_rmvpe_onnx=5370e71ac80af8b4b7c793d27efd51fd8bf962de3a7ede0766dac0befa3660fd \
    sha256_v1_D32k_pth=2ab20645829460fdad0d3c44254f1ab53c32cae50c22a66c926ae5aa30abda6f \
    sha256_v1_D40k_pth=547f66dbbcd9023b9051ed244d12ab043ba8a4e854b154cc28761ac7c002909b \
    sha256_v1_D48k_pth=8cc013fa60ed9c3f902f5bd99f48c7e3b9352d763d4d3cd6bc241c37b0bfd9ad \
    sha256_v1_G32k_pth=81817645cde7ed2e2d83f23ef883f33dda564924b497e84d792743912eca4c23 \
    sha256_v1_G40k_pth=e428573bda1124b0ae0ae843fd8dcded6027d3993444790b3e9b0100938b2113 \
    sha256_v1_G48k_pth=3862a67ea6313e8ffefc05cee6bee656ef3e089442e9ecf4a6618d60721f3e95 \
    sha256_v1_f0D32k_pth=294db3087236e2c75260d6179056791c9231245daf5d0485545d9e54c4057c77 \
    sha256_v1_f0D40k_pth=7d4f5a441594b470d67579958b2fd4c6b992852ded28ff9e72eda67abcebe423 \
    sha256_v1_f0D48k_pth=1b84c8bf347ad1e539c842e8f2a4c36ecd9e7fb23c16041189e4877e9b07925c \
    sha256_v1_f0G32k_pth=285f524bf48bb692c76ad7bd0bc654c12bd9e5edeb784dddf7f61a789a608574 \
    sha256_v1_f0G40k_pth=9115654aeef1995f7dd3c6fc4140bebbef0ca9760bed798105a2380a34299831 \
    sha256_v1_f0G48k_pth=78bc9cab27e34bcfc194f93029374d871d8b3e663ddedea32a9709e894cc8fe8 \
    sha256_v2_D32k_pth=d8043378cc6619083d385f5a045de09b83fb3bf8de45c433ca863b71723ac3ca \
    sha256_v2_D40k_pth=471378e894e7191f89a94eda8288c5947b16bbe0b10c3f1f17efdb7a1d998242 \
    sha256_v2_D48k_pth=db01094a93c09868a278e03dafe8bb781bfcc1a5ba8df168c948bf9168c84d82 \
    sha256_v2_G32k_pth=869b26a47f75168d6126f64ac39e6de5247017a8658cfd68aca600f7323efb9f \
    sha256_v2_G40k_pth=a3843da7fde33db1dab176146c70d6c2df06eafe9457f4e3aa10024e9c6a4b69 \
    sha256_v2_G48k_pth=2e2b1581a436d07a76b10b9d38765f64aa02836dc65c7dee1ce4140c11ea158b \
    sha256_v2_f0D32k_pth=bd7134e7793674c85474d5145d2d982e3c5d8124fc7bb6c20f710ed65808fa8a \
    sha256_v2_f0D40k_pth=6b6ab091e70801b28e3f41f335f2fc5f3f35c75b39ae2628d419644ec2b0fa09 \
    sha256_v2_f0D48k_pth=2269b73c7a4cf34da09aea99274dabf99b2ddb8a42cbfb065fb3c0aa9a2fc748 \
    sha256_v2_f0G32k_pth=2332611297b8d88c7436de8f17ef5f07a2119353e962cd93cda5806d59a1133d \
    sha256_v2_f0G40k_pth=3b2c44035e782c4b14ddc0bede9e2f4a724d025cd073f736d4f43708453adfcb \
    sha256_v2_f0G48k_pth=b5d51f589cc3632d4eae36a315b4179397695042edc01d15312e1bddc2b764a4 \
    sha256_uvr5_HP2-人声vocals+非人声instrumentals_pth=39796caa5db18d7f9382d8ac997ac967bfd85f7761014bb807d2543cc844ef05 \
    sha256_uvr5_HP2_all_vocals_pth=39796caa5db18d7f9382d8ac997ac967bfd85f7761014bb807d2543cc844ef05 \
    sha256_uvr5_HP3_all_vocals_pth=45e6b65199e781b4a6542002699be9f19cd3d1cb7d1558bc2bfbcd84674dfe28 \
    sha256_uvr5_HP5-主旋律人声vocals+其他instrumentals_pth=5908891829634926119720241e8573d97cbeb8277110a7512bdb0bd7563258ee \ 
    sha256_uvr5_HP5_only_main_vocal_pth=5908891829634926119720241e8573d97cbeb8277110a7512bdb0bd7563258ee \
    sha256_uvr5_VR-DeEchoAggressive_pth=8c8fd1582f9aabc363e47af62ddb88df6cae7e064cae75bbf041a067a5e0aee2 \
    sha256_uvr5_VR-DeEchoDeReverb_pth=01376dd2a571bf3cb9cced680732726d2d732609d09216a610b0d110f133febe \
    sha256_uvr5_VR-DeEchoNormal_pth=56aba59db3bcdd14a14464e62f3129698ecdea62eee0f003b9360923eb3ac79e \
    sha256_uvr5_vocals_onnx=233bb5c6aaa365e568659a0a81211746fa881f8f47f82d9e864fce1f7692db80

VOLUME [ "/app/weights", "/app/opt" ]

CMD ["python3", "run.py"]
