from pydantic import BaseModel, Field


class AttractionSearchdata(BaseModel):
    id: str = Field(description="景点ID")
    name: str = Field(description="单个景点名称")
    address: str = Field(description="单个景点地址")
    photo_url: str = Field(description="单个景点照片URL")
    typecode: str = Field(description="景点类型编码")


class AttractionResult(BaseModel):
    attractions: list[AttractionSearchdata] = Field(description="景点搜索结果列表")


class HotelSearchdata(BaseModel):
    id: str = Field(description="酒店ID")
    name: str = Field(description="酒店名称")
    address: str = Field(description="酒店地址")
    photo_url: str = Field(description="酒店照片URL")
    typecode: str = Field(description="酒店类型编码")


class HotelResult(BaseModel):
    hotels: list[HotelSearchdata] = Field(description="酒店搜索结果列表")
