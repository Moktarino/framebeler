# Framebeler: A tool to label video frames for Deep Learning


Framebeler takes a directory of videos and presents them to you frame by frame with an interface to label each frame.
It outputs a json file containing the labels indexed against the frames, grouped by the video file's hash, e.g.: 

```json
{
   "labels":[
      "test1",
      "test2",
      "test3"
   ],
   "label_maps":{
      "02482155855FCD65019D7D672D95E595":{
         "0":[
            
         ],
         "51":[
            "test2"
         ],
         "132":[
            "test2",
            "test3"
         ],
         "279":[
            "test3",
            "test1",
            "test2"
         ]
      },
      "E5932C404ADE87FF3E393DB03F6E0F93":{
         "0":[
            
         ],
         "25":[
            "test2"
         ],
         "161":[
            "test3",
            "test1"
         ]
      },
      "23FC361127371FAE46A41C546DB3FAA2":{
         "0":[
            
         ],
         "27":[
            "test2"
         ],
         "101":[
            "test2"
         ],
         "140":[
            
         ]
      }
   }
}
```
