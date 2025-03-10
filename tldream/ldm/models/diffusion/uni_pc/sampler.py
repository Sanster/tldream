"""SAMPLING ONLY."""

import torch

from .uni_pc import NoiseScheduleVP, model_wrapper, UniPC


class UniPCSampler(object):
    def __init__(self, model, device, torch_dtype, **kwargs):
        super().__init__()
        self.model = model
        self.device = device
        self.torch_dtype = torch_dtype
        to_torch = lambda x: x.clone().detach().to(torch_dtype).to(self.device)
        self.register_buffer("alphas_cumprod", to_torch(model.alphas_cumprod))

    def register_buffer(self, name, attr):
        if type(attr) == torch.Tensor:
            attr = attr.to(self.torch_dtype)
            attr = attr.to(torch.device(self.device))
        setattr(self, name, attr)

    @torch.no_grad()
    def sample(
        self,
        S,
        batch_size,
        shape,
        conditioning=None,
        callback=None,
        normals_sequence=None,
        img_callback=None,
        quantize_x0=False,
        eta=0.0,
        mask=None,
        x0=None,
        temperature=1.0,
        noise_dropout=0.0,
        score_corrector=None,
        corrector_kwargs=None,
        verbose=True,
        x_T=None,
        log_every_t=100,
        unconditional_guidance_scale=1.0,
        unconditional_conditioning=None,
        # this has to come in the same format as the conditioning, # e.g. as encoded tokens, ...
        **kwargs,
    ):
        if conditioning is not None:
            if isinstance(conditioning, dict):
                ctmp = conditioning[list(conditioning.keys())[0]]
                while isinstance(ctmp, list):
                    ctmp = ctmp[0]
                cbs = ctmp.shape[0]
                if cbs != batch_size:
                    print(
                        f"Warning: Got {cbs} conditionings but batch-size is {batch_size}"
                    )

            elif isinstance(conditioning, list):
                for ctmp in conditioning:
                    if ctmp.shape[0] != batch_size:
                        print(
                            f"Warning: Got {cbs} conditionings but batch-size is {batch_size}"
                        )

            else:
                if conditioning.shape[0] != batch_size:
                    print(
                        f"Warning: Got {conditioning.shape[0]} conditionings but batch-size is {batch_size}"
                    )

        # sampling
        C, H, W = shape
        size = (batch_size, C, H, W)

        device = self.model.betas.device
        if x_T is None:
            img = torch.randn(size, device=device, dtype=self.torch_dtype)
        else:
            img = x_T

        ns = NoiseScheduleVP("discrete", alphas_cumprod=self.alphas_cumprod)

        model_fn = model_wrapper(
            lambda x, t, c: self.model.apply_model(x, t, c),
            ns,
            model_type="noise",
            guidance_type="classifier-free",
            condition=conditioning,
            unconditional_condition=unconditional_conditioning,
            guidance_scale=unconditional_guidance_scale,
        )

        uni_pc = UniPC(model_fn, ns, predict_x0=True, thresholding=False)
        x = uni_pc.sample(
            img,
            steps=S,
            skip_type="time_uniform",
            method="multistep",
            order=3,
            lower_order_final=True,
            img_callback=img_callback,
        )

        return x.to(device)
