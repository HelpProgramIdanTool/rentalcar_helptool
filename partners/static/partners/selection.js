(function(root){
 class UniqueGroupSelection{
  constructor(ids,selected=[]){
   this.ids=ids.map(String);this.owners=new Map();
   const wanted=new Set(selected.map(String));
   this.ids.forEach((id,index)=>{if(wanted.has(id)&&!this.owners.has(id))this.owners.set(id,index);});
  }
  set(index,checked){
   if(!Number.isInteger(index)||index<0||index>=this.ids.length)return false;
   const id=this.ids[index],owner=this.owners.get(id);
   if(checked){if(owner!==undefined&&owner!==index)return false;this.owners.set(id,index);}
   else if(owner===index)this.owners.delete(id);
   return true;
  }
  state(index){const owner=this.owners.get(this.ids[index]);return {checked:owner===index,already:owner!==undefined&&owner!==index,source:owner};}
  selectedIds(){return [...this.owners.keys()];}
 }
 if(typeof module!=='undefined'&&module.exports)module.exports=UniqueGroupSelection;
 else root.PartnerSelection=UniqueGroupSelection;
})(typeof globalThis!=='undefined'?globalThis:this);
