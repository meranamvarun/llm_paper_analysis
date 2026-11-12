from .automated_quality import tokens

def consensus(a,b):
    return a.strip() if tokens(a) and tokens(a)==tokens(b) else None

def decode_field_image(stream):
    from pypdf.filters import FlateDecode
    from PIL import Image
    if stream.get('/Filter')!='/FlateDecode' or int(stream.get('/BitsPerComponent',0))!=8:raise ValueError('Unsupported image encoding')
    mode={'/DeviceCMYK':'CMYK','/DeviceRGB':'RGB','/DeviceGray':'L'}.get(str(stream.get('/ColorSpace')))
    if mode is None:raise ValueError('Unsupported image colorspace')
    parms=stream.get('/DecodeParms')
    if parms is not None:parms=parms.get_object()
    data=FlateDecode.decode(stream._data,parms)
    width,height=int(stream['/Width']),int(stream['/Height']);channels={'CMYK':4,'RGB':3,'L':1}[mode]
    if len(data)!=width*height*channels:raise ValueError('Decoded image length mismatch')
    return Image.frombytes(mode,(width,height),data).convert('RGB')



def field_source_support(question,group):
    from .automated_quality import compare_text
    from .strict_support import strict_supported
    expected=['stem','option_A','option_B','option_C','option_D']
    if set(group)!=set(expected):return None
    selected=[];parts=[]
    for field in expected:
        target=question['stem'] if field=='stem' else question['options']['ABCD'.index(field[-1])]['text']
        candidates=[]
        for r in group[field]['readings']:
            if r['returncode']:continue
            check=compare_text(target,r['text'])
            if strict_supported(check):candidates.append((r,check))
        if not candidates:return None
        r,check=candidates[0];selected.append({'field':field,'reading':r,'comparison':check})
        parts.append(('' if field=='stem' else str('ABCD'.index(field[-1])+1)+'. ')+r['text'])
    return {'source_text':'\n'.join(parts),'fields':selected}
