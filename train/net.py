import torch
from torch import nn
from einops import repeat

from vit_pytorch import ViT
from vit_pytorch.vit import Transformer


class NET(nn.Module):
    def __init__(
        self,
        *,
        encoder,
        decoder_dim,
        output_size,
        decoder_depth = 1,
        decoder_heads = 8,
        decoder_dim_head = 64
    ):
        super().__init__()

        # extract some hyperparameters and functions from encoder (vision transformer to be trained)

        self.encoder = encoder
        num_patches, encoder_dim = encoder.pos_embedding.shape[-2:]
        self.to_patch, self.patch_to_emb = encoder.to_patch_embedding[:2]

        # decoder parameters

        self.enc_to_dec = nn.Linear(encoder_dim, decoder_dim) if encoder_dim != decoder_dim else nn.Identity()
        self.mask_token = nn.Parameter(torch.randn(decoder_dim))
        self.decoder = Transformer(dim = decoder_dim, depth = decoder_depth, heads = decoder_heads, dim_head = decoder_dim_head, mlp_dim = decoder_dim * 4)
        self.decoder_pos_emb = nn.Embedding(num_patches, decoder_dim)
        self.to_pixels = nn.Linear(decoder_dim, output_size)

    def forward(self, scRNA):
        device = scRNA.device

        # get patches

        patches = self.to_patch(scRNA)
        batch, num_patches, *_ = patches.shape

        # patch to encoder tokens and add positions

        tokens = self.patch_to_emb(patches)
        tokens = tokens + self.encoder.pos_embedding[:, 1:(num_patches + 1)]

        # attend with vision transformer

        encoded_tokens = self.encoder.transformer(tokens)

        # project encoder to decoder dimensions

        decoder_tokens = self.enc_to_dec(encoded_tokens)

        # reapply decoder position embedding to tokens

        indices = repeat(torch.arange(num_patches, device = device), 'd -> b d', b = batch)
        decoder_tokens = decoder_tokens + self.decoder_pos_emb(indices)

        # attend with decoder

        decoded_tokens = self.decoder(decoder_tokens)

        # project to pixel values

        pred_tokens = repeat(decoded_tokens.mean(dim = 1), 'b d -> b c d', c = 1)
        pred_pixel_values = self.to_pixels(pred_tokens)

        return pred_pixel_values


def define_network(input_size, patch_size, output_size):
    v = ViT(
        image_size = input_size,
        patch_size = patch_size,
        num_classes = 1000,
        dim = 1024,
        depth = 6,
        heads = 8,
        mlp_dim = 2048,
        channels = 1
    )

    network = NET(
        encoder = v,
        decoder_dim = 512,
        output_size = output_size,
        decoder_depth = 6
    )

    return network