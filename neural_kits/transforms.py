import torch
import numpy as np

class Pair_Compose:
    '''
    pair-wise augmentation like simclr or byol to create pairs
    '''
    def __init__(self, *transforms):
        self.transforms = transforms

    def __call__(self, x):
        x1 = x.clone()
        x2 = x.clone()
        for transform in self.transforms:
            x1 = transform(x1)
        for transform in self.transforms:
            x2 = transform(x2)

        if torch.eq(x1, x2).all():
            print("manual alert, x1 and x2 are the same")
        return x1, x2


class Compose:
    r"""Composes several transforms together.
    Args:
        transforms (Callable): List of transforms to compose.
    """
    def __init__(self, *transforms):
        self.transforms = transforms

    def __call__(self, x):
        for transform in self.transforms:
            # print(x.shape)
            x = transform(x)
            # print(transform, x.shape)
        return x


class Dropout:
    r"""Drops a neuron with a probability of :obj:`p`.
    .. note::
        If more than one tensor is given, the same dropout pattern will be applied to all.
    Args:
        p (float, Optional): Probability of dropout. (default: :obj:`0.5`)
        apply_p (float, Optional): Probability of applying the transformation. (default: :obj:`1.0`)
        scale (float, Optional): If :obj:`True`, the activity of the neurons are scaled to account for the decrease in
            overall activity. (default: :obj:`False`)
    """
    def __init__(self, p: float = 0.5, apply_p=1.):
        self.p = p
        self.apply_p = apply_p

    def __call__(self, x):
        # create dropout mask (batch_size, num_neurons)
        dropout_mask = torch.rand(x.shape) < 1 - self.p
        # create apply mask: (batch_size,)
        apply_mask = torch.rand(x.shape) < 1 - self.apply_p
        dropout_mask = dropout_mask + apply_mask.view((-1, 1))
        return x * dropout_mask.to(x)


class FixedDropout:
    r"""Same as dropout but only applies to a single Tensor at a time
    """
    def __init__(self, p: float = 0.5, apply_p=1.):
        self.p = p
        self.apply_p = apply_p

    def __call__(self, x):
        dropout_mask = torch.rand(x.shape) < 1 - self.p
        apply_mask = torch.rand(x.shape) < 1 - self.apply_p
        dropout_mask = dropout_mask + apply_mask
        return x * dropout_mask.to(x)


class RandomizedDropout:
    r"""Drops a neuron with a random probability uniformly sampled between :obj:`0` and :obj:`p`.
    .. note::
        If more than one tensor is given, the same dropout pattern will be applied to all.
    Args:
        p (float, Optional): Upper bound for the probability of dropout. (default: :obj:`0.5`)
        apply_p (float, Optional): Probability of applying the transformation. (default: :obj:`1.0`)
        scale (float, Optional): If :obj:`True`, the activity of the neurons are scaled to account for the decrease in
            overall activity. (default: :obj:`False`)
    """
    def __init__(self, p: float = 0.5, apply_p=1.):
        self.p = p
        self.apply_p = apply_p

    def __call__(self, x):
        # generate a random dropout probability for each sample
        p = torch.rand(x.shape) * self.p
        # generate dropout mask
        dropout_mask = torch.rand(x.shape) < 1 - p
        # generate mask for applying dropout
        apply_mask = torch.rand(x.shape) < 1 - self.apply_p
        dropout_mask = dropout_mask + apply_mask
        r_x = x * dropout_mask.to(x)
        return r_x


class EntrywiseDropout:
    r"""
    Drops out each individual neuron in the dataset according to its own
    fixed probability p.
    """
    def __init__(self, p, apply_p=1.):
        self.p = p
        self.apply_p = apply_p

    def __call__(self, x):
        dropout_mask = torch.rand(x.shape) < 1 - self.p
        apply_mask = torch.rand(x.shape) < 1 - self.apply_p
        dropout_mask += apply_mask
        return x * dropout_mask.to(x)


# TODO: needs testing, address dropout scaling issue
class DistributedDropout:
    r"""
    Applies dropout to a given tensor given a distribution generator,
    mathematical transform, and application probability
    
    Args:
        dist: distribution to draw random numbers from, based on
        numpy.random.Generator
        p (Tensor): probability of applying dropout given sample values
        m (lambda expr): mathematical transform to perform on sampled values,
        default identity
        kwargs: parameters for dist
    """
    def __init__(self, p, apply_p=1., dist=np.random.rand, m=None, **kwargs):
        self.dist = dist
        self.p = p
        self.apply_p = apply_p
        if m is None:
            self.m = lambda x: x
        self.kwargs = kwargs

    def set_args(**kwargs):
        self.kwargs = kwargs

    def __call__(self, x):
        s = self.dist(**(self.kwargs), size=tuple(x.shape))
        ms = self.m(s)
        dropout_mask = ms < 1 - self.p
        apply_mask = torch.rand(x.shape) < 1 - self.apply_p
        dropout_mask += apply_mask
        return x * mask


class Noise:
    r"""Adds Gaussian noise to neural activity. The firing rate vector needs to have already been normalized, and
        the Gaussian noise is center and has standard deviation of :obj:`std`.
    .. note::
        If more than one tensor is given, the same dropout pattern will be applied to all.
    Args:
        std (float): Standard deviation of Gaussian noise.
    """
    def __init__(self, std):
        self.std = std

    def __call__(self, *x_list):
        if self.std == 0:
            return x_list
        noise = torch.normal(0.0, self.std, size=x_list[0].size())
        return [x + noise.to(x) for x in x_list]


class Pepper:
    r"""Adds a constant to the neuron firing rate with a probability of :obj:`p`. The firing rate vector needs to have
        already been normalized.
    .. note::
        If more than one tensor is given, the same dropout pattern will be applied to all.
    Args:
        p (float, Optional): Probability of adding pepper. (default: :obj:`0.5`)
        apply_p (float, Optional): Probability of applying the transformation. (default: :obj:`1.0`)
        sigma (float, Optional): Constant to be added to neural activity. (default: :obj:`1.0`)
    """
    def __init__(self, p=0.5, sigma=1.0, apply_p=1.):
        self.p = p
        self.sigma = sigma
        self.apply_p = apply_p

    def __call__(self, x):
        keep_mask = torch.rand(x.shape) < self.p
        random_pepper = self.sigma * keep_mask
        apply_mask = torch.rand(x.shape) < self.apply_p
        random_pepper = random_pepper * apply_mask
        return x + random_pepper.to(x)


class Normalize:
    r"""Normalization transform.
    Args:
        mean (torch.Tensor): Mean.
        std (torch.Tensor): Standard deviation.
    """
    def __init__(self, mean, std):
        self.mean = mean
        self.std = std

    def __call__(self, x):
        # ?
        return torch.div(x - self.mean.to(x), self.std.to(x))


#### originally
class Origin_Compose:
    r"""Composes several transforms together.
    Args:
        transforms (Callable): List of transforms to compose.
    """
    def __init__(self, *transforms):
        self.transforms = transforms

    def __call__(self, *x):
        for transform in self.transforms:
            x = transform(*x)
        return x

class Origin_RandomizedDropout:
    r"""Drops a neuron with a random probability uniformly sampled between :obj:`0` and :obj:`p`.
    .. note::
        If more than one tensor is given, the same dropout pattern will be applied to all.
    Args:
        p (float, Optional): Upper bound for the probability of dropout. (default: :obj:`0.5`)
        apply_p (float, Optional): Probability of applying the transformation. (default: :obj:`1.0`)
        scale (float, Optional): If :obj:`True`, the activity of the neurons are scaled to account for the decrease in
            overall activity. (default: :obj:`False`)
    """
    def __init__(self, p: float = 0.5, apply_p=1.):
        self.p = p
        self.apply_p = apply_p

    def __call__(self, *x_list):
        # generate a random dropout probability for each sample
        p = torch.rand(x_list[0].size(0)) * self.p
        # generate dropout mask
        dropout_mask = torch.rand(x_list[0].size()) < 1 - p.view((-1, 1))
        # generate mask for applying dropout
        apply_mask = torch.rand(x_list[0].size(0)) < 1 - self.apply_p
        dropout_mask = dropout_mask + apply_mask.view((-1, 1))
        return [x * dropout_mask.to(x) for x in x_list]

class Origin_Pepper:
    r"""Adds a constant to the neuron firing rate with a probability of :obj:`p`. The firing rate vector needs to have
        already been normalized.
    .. note::
        If more than one tensor is given, the same dropout pattern will be applied to all.
    Args:
        p (float, Optional): Probability of adding pepper. (default: :obj:`0.5`)
        apply_p (float, Optional): Probability of applying the transformation. (default: :obj:`1.0`)
        sigma (float, Optional): Constant to be added to neural activity. (default: :obj:`1.0`)
    """
    def __init__(self, p=0.5, sigma=1.0, apply_p=1.):
        self.p = p
        self.sigma = sigma
        self.apply_p = apply_p

    def __call__(self, *x_list):
        keep_mask = torch.rand(x_list[0].size()) < self.p
        random_pepper = self.sigma * keep_mask
        apply_mask = torch.rand(x_list[0].size(0)) < self.apply_p
        random_pepper = random_pepper * apply_mask.view((-1, 1))
        return [x + random_pepper.to(x) for x in x_list]
